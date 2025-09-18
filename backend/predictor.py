# predictor_service.py
import json
from multiprocessing import Process, Queue
from time import sleep
import pandas as pd
import joblib
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from kafka import KafkaConsumer
from sqlalchemy import create_engine, Integer, Column, Float, String
from sqlalchemy.orm import sessionmaker, declarative_base
from contextlib import asynccontextmanager
import asyncio
import pprint

# DB setup
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

# Load model
xgb_model = joblib.load("xgboost.pkl")
HIGH_ALERT_THRESHOLD = 0.8

# Kafka queue
message_queue = Queue()
alert_connections = []

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
            print("\n[DEBUG] Predicted transaction:")
            pprint.pprint(txn)
        
            try:
                db.add(Transaction(**txn))
                db.commit()
            except:
                db.rollback()
            queue.put(txn)  # push every transaction to WebSocket

async def broadcast_loop():
    while True:
        while not message_queue.empty():
            txn = message_queue.get()
            payload = {"transaction": txn}
            for ws in list(alert_connections):
                try:
                    await ws.send_json(payload)
                except WebSocketDisconnect:
                    alert_connections.remove(ws)
        await sleep(0.01)

@asynccontextmanager
async def lifespan(app: FastAPI):
    p = Process(target=predictor_worker, args=(message_queue,))
    p.daemon = True
    p.start()
    import asyncio
    loop = asyncio.get_event_loop()
    loop.create_task(broadcast_loop())
    yield
    p.terminate()
    p.join()

app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

@app.websocket("/ws/alerts")
async def alerts_ws(websocket: WebSocket):
    await websocket.accept()
    alert_connections.append(websocket)
    try:
        while True:
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        alert_connections.remove(websocket)
