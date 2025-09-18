from fastapi import FastAPI
from ctgan import CTGAN
from kafka import KafkaProducer
import json
from time import sleep
import threading

gen_model=CTGAN.load('ctgan_model.pkl')

app = FastAPI()

producer = KafkaProducer(
    bootstrap_servers="localhost:9092",
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

generator_thread = None

MAX_BYTES=10*1024*1024
stop_event=threading.Event()
status='idle'

def generate(batch_size=200, sub_batch_size=10, max_bytes=MAX_BYTES, sleep_time=1):
    global status
    sent_bytes = 0
    status = "processing"

    while not stop_event.is_set():
        df = gen_model.sample(batch_size)
        records = df.to_dict(orient="records")

        for i in range(0, batch_size, sub_batch_size):
            sub_batch = records[i:i+sub_batch_size]
            data = json.dumps(sub_batch).encode("utf-8")
            size = len(data)

            if sent_bytes + size > max_bytes:
                stop_event.set()
                break  # exit inner loop

            producer.send("transaction-topic", sub_batch)
            sent_bytes += size

        producer.flush()

        # Small sleep with responsive stop check
        for _ in range(int(sleep_time * 10)):
            if stop_event.is_set():
                break
            sleep(0.1)

    # Loop exited → mark stopped
    status = "stopped"


@app.post("/start")
def start():
    global generator_thread, stop_event, status
    if status == "processing":
        return {"status": "already running"}

    stop_event.clear()
    generator_thread = threading.Thread(target=generate, daemon=True)
    generator_thread.start()
    return {"status": "started"}

@app.post("/stop")
def stop():
    global stop_event, status
    stop_event.set()
    status = "stopped"
    return {"status": "stopping"}

@app.get("/status")
def get_status():
    return {"status": status}
