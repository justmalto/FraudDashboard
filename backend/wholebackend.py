# combined_service.py
import json
import threading
from time import sleep
from multiprocessing import Process, Queue
import asyncio
import pandas as pd
import joblib

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from ctgan import CTGAN
from kafka import KafkaProducer, KafkaConsumer
from sqlalchemy import create_engine, Integer, Column, Float, String
from sqlalchemy.orm import sessionmaker, declarative_base
from contextlib import asynccontextmanager
import pprint

# -----------------------------
# DATABASE SETUP
# -----------------------------
DATABASE_URL = "sqlite:///./ccfraud.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    distance_from_home = Column(Float)
    distance_from_last_transaction = Column(Float)
    ratio_to_median_purchase_price = Column(Float)
    repeat_retailer = Column(Integer)
    used_chip = Column(Integer)
    used_pin_number = Column(Integer)
    online_order = Column(Integer)
    risk_score = Column(Float)
    timestamp = Column(String)

Base.metadata.create_all(bind=engine)

# -----------------------------
# LOAD MODELS
# -----------------------------
gen_model = CTGAN.load("ctgan_model.pkl")
xgb_model = joblib.load("xgboost.pkl")
HIGH_ALERT_THRESHOLD = 0.8

# -----------------------------
# KAFKA SETUP
# -----------------------------
producer = KafkaProducer(
    bootstrap_servers="localhost:9092",
    value_serializer=lambda v: json.dumps(v).encode("utf-8")
)
MAX_BYTES = 100 * 1024 * 1024

# -----------------------------
# GLOBAL STATE
# -----------------------------
generator_thread = None
stop_event_generator = threading.Event()
status_generator = "idle"

message_queue = Queue()
alert_connections = []
analytics_connections = []

# -----------------------------
# GENERATOR FUNCTION
# -----------------------------
def generate(batch_size=20, sub_batch_size=10, max_bytes=MAX_BYTES, sleep_time=1):
    global status_generator
    sent_bytes = 0
    status_generator = "processing"

    while not stop_event_generator.is_set():
        df = gen_model.sample(batch_size)
        records = df.to_dict(orient="records")

        for i in range(0, batch_size, sub_batch_size):
            sub_batch = records[i:i+sub_batch_size]
            data = json.dumps(sub_batch).encode("utf-8")
            size = len(data)

            if sent_bytes + size > max_bytes:
                stop_event_generator.set()
                break

            producer.send("transaction-topic", sub_batch)
            sent_bytes += size

        producer.flush()

        # Responsive sleep
        for _ in range(int(sleep_time * 10)):
            if stop_event_generator.is_set():
                break
            sleep(0.01)

    status_generator = "stopped"

# -----------------------------
# PREDICTOR FUNCTION
# -----------------------------
def predictor_worker(queue: Queue):
    db = SessionLocal()
    consumer = KafkaConsumer(
        "transaction-topic",
        bootstrap_servers="localhost:9092",
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        auto_offset_reset="latest"
    )

    for message in consumer:
        sub_batch = message.value
        df = pd.DataFrame(sub_batch)
        df["risk_score"] = xgb_model.predict(df)

        for txn in df.to_dict(orient="records"):
            txn["timestamp"] = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
            pprint.pprint(txn)
            try:
                db.add(Transaction(**txn))
                db.commit()
            except:
                db.rollback()
            queue.put(txn)

# -----------------------------
# ANALYTICS FUNCTION
# -----------------------------
def compute_histogram(df, column, bins=5):
    df["bin"] = pd.cut(df[column], bins=bins)
    grouped = df.groupby(["bin", "risk_score"]).size().unstack(fill_value=0)
    if 0 not in grouped.columns:
        grouped[0] = 0
    if 1 not in grouped.columns:
        grouped[1] = 0
    hist_data = []
    for bin_idx, row in grouped.iterrows():
        hist_data.append({
            "bin": str(bin_idx),
            "safe": int(row[0]),
            "fraud": int(row[1])
        })
    return hist_data

async def broadcast_loop():
    while True:
        # ALERTS
        while not message_queue.empty():
            txn = message_queue.get()
            payload = {"transaction": txn}
            for ws in list(alert_connections):
                try:
                    await ws.send_json(payload)
                except WebSocketDisconnect:
                    alert_connections.remove(ws)

        # ANALYTICS
        db = SessionLocal()
        try:
            df = pd.read_sql(
                "SELECT distance_from_home, distance_from_last_transaction, ratio_to_median_purchase_price, risk_score FROM transactions",
                db.bind
            )
            if not df.empty:
                payload = {
                    "fraud_count": int((df["risk_score"] == 1).sum()),
                    "safe_count": int((df["risk_score"] == 0).sum()),
                    "distance_from_home_hist": compute_histogram(df, "distance_from_home"),
                    "distance_from_last_transaction_hist": compute_histogram(df, "distance_from_last_transaction"),
                    "purchase_ratio_hist": compute_histogram(df, "ratio_to_median_purchase_price")
                }
                for ws in list(analytics_connections):
                    try:
                        await ws.send_json(payload)
                    except WebSocketDisconnect:
                        analytics_connections.remove(ws)
        finally:
            db.close()
        await asyncio.sleep(0.1)

# -----------------------------
# FASTAPI APP
# -----------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start predictor process
    p = Process(target=predictor_worker, args=(message_queue,))
    p.daemon = True
    p.start()

    # Start broadcast loop
    loop = asyncio.get_event_loop()
    loop.create_task(broadcast_loop())

    yield

    # Cleanup
    stop_event_generator.set()
    p.terminate()
    p.join()

app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# -----------------------------
# GENERATOR ENDPOINTS
# -----------------------------
@app.post("/start")
def start_generator():
    global generator_thread, stop_event_generator, status_generator
    if status_generator == "processing":
        return {"status": "already running"}
    stop_event_generator.clear()
    generator_thread = threading.Thread(target=generate, daemon=True)
    generator_thread.start()
    return {"status": "started"}

@app.post("/stop")
def stop_generator():
    global stop_event_generator, status_generator
    stop_event_generator.set()
    status_generator = "stopped"
    return {"status": "stopping"}

@app.get("/status")
def get_status():
    return {"status": status_generator}

# -----------------------------
# WEBSOCKET ENDPOINTS
# -----------------------------
@app.websocket("/ws/alerts")
async def alerts_ws(websocket: WebSocket):
    await websocket.accept()
    alert_connections.append(websocket)
    try:
        while True:
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        alert_connections.remove(websocket)

@app.websocket("/ws/analytics")
async def analytics_ws(websocket: WebSocket):
    await websocket.accept()
    analytics_connections.append(websocket)
    try:
        while True:
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        analytics_connections.remove(websocket)
