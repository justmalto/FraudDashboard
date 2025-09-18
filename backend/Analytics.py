# analytics_service.py
import asyncio
import pandas as pd
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from contextlib import asynccontextmanager

DATABASE_URL = "sqlite:///./ccfraud.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)

analytics_connections = []

def compute_histogram(df, column, bins=5):
    """Returns list of dicts for each bin with counts of safe and fraud."""
    df["bin"] = pd.cut(df[column], bins=bins)
    grouped = df.groupby(["bin", "risk_score"]).size().unstack(fill_value=0)
    # Ensure both risk categories exist
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

async def analytics_broadcast_loop(stop_event: asyncio.Event):
    while not stop_event.is_set():
        db = SessionLocal()
        try:
            df = pd.read_sql(
                "SELECT distance_from_home, distance_from_last_transaction, ratio_to_median_purchase_price, risk_score FROM transactions",
                db.bind
            )
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
        await asyncio.sleep(1)

@asynccontextmanager
async def lifespan(app: FastAPI):
    stop_event = asyncio.Event()
    task = asyncio.create_task(analytics_broadcast_loop(stop_event))
    yield
    stop_event.set()
    await task

app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.websocket("/ws/analytics")
async def analytics_ws(websocket: WebSocket):
    await websocket.accept()
    analytics_connections.append(websocket)
    try:
        while True:
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        analytics_connections.remove(websocket)
