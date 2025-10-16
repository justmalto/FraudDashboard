
# 🧠 Credit Card Fraud Dashboard Pipeline

**(TableGAN + XGBoost + FastAPI + Kafka + React)**

---

## 🚀 Overview

This project implements a **complete end-to-end fraud detection system** that integrates **synthetic data generation**, **machine learning classification**, and **real-time streaming**.

It combines:

* **TableGAN** for generating synthetic credit-card transaction data
* **XGBoost** for detecting fraudulent activity
* **FastAPI** for exposing generation and prediction endpoints
* **Kafka (Bitnami Docker)** for distributed message streaming
* **SQLite** for lightweight persistence
* **React + WebSockets + Chart.js** for real-time visualization

---

## 🧩 System Architecture

![System Architecture](https://github.com/user-attachments/assets/30d9e29e-a5a0-41c7-8db3-d132b28108c8)


## 🧰 Technologies Used

| Category                  | Tool                              |
| ------------------------- | --------------------------------- |
| **ML / AI**               | XGBoost, TableGAN, SMOTE          |
| **Experiment Tracking**   | MLflow                            |
| **Backend Framework**     | FastAPI                           |
| **Streaming / Messaging** | **Apache Kafka (Bitnami Docker)** |
| **Database**              | SQLite                            |
| **Frontend**              | React, WebSockets, Chart.js       |
| **Containerization**      | Docker                            |

---

## ⚙️ Setup Instructions

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/fraud-detection-pipeline.git
cd fraud-detection-pipeline
```

---

### 2. Set up Python environment

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

### 3. Run MLflow (optional)

```bash
mlflow ui --port 5000
```

---

### 4. Start Kafka (Bitnami Docker)

This project uses **Bitnami Docker images** for Kafka and Zookeeper to ensure consistent, portable deployment.

```bash
# Create network
docker network create kafka-net

# Start Zookeeper
docker run -d --name zookeeper --network kafka-net \
  -e ALLOW_ANONYMOUS_LOGIN=yes \
  bitnami/zookeeper:latest

# Start Kafka broker
docker run -d --name kafka --network kafka-net \
  -e KAFKA_CFG_ZOOKEEPER_CONNECT=zookeeper:2181 \
  -e ALLOW_PLAINTEXT_LISTENER=yes \
  -p 9092:9092 \
  bitnami/kafka:latest
```

> 🧩 *Kafka and Zookeeper run in Docker containers using Bitnami’s images for reliability and quick local setup.*

---

### 5. Start FastAPI backend

```bash
uvicorn app.main:app --reload
```

---

### 6. Start React frontend

```bash
cd frontend
npm install
npm start
```

---

## 🔄 Data Flow

1. User/API requests data generation → `/generate` endpoint (TableGAN).
2. Synthetic transactions are streamed to **Kafka Producer**.
3. Kafka Consumer receives data and routes to **XGBoost fraud detector**.
4. Predictions and metadata are stored in **SQLite**.
5. **WebSockets** stream results in real time to the React dashboard.
6. **Chart.js** visualizes fraud ratios, trends, and model metrics.

---

## 📊 Analytics Dashboard

* Fraud vs Non-Fraud distribution
* Prediction confidence histograms
* Model accuracy / recall / precision metrics
* Synthetic vs Real transaction insights
* Time-based fraud detection patterns

---

## 🧠 Model Training Summary

* Dataset imbalance: **91.8 % non-fraud, 8.2 % fraud**
* Oversampling: **SMOTE** applied for balance
* Model: **XGBoost** (best performer during MLflow experiments)
* Synthetic data source: **TableGAN** trained on original dataset
* Tracked using **MLflow** for reproducibility

---

## 🧩 Future Improvements

* Replace SQLite → PostgreSQL for scalability
* Add **Docker Compose** for one-command startup
* Deploy backend + Kafka on **Kubernetes**
* Introduce **incremental learning** for streaming adaptation
* Integrate **Grafana / Prometheus** for system monitoring

---

## 🧑‍💻 Author

**Omkar Kar**
Machine Learning Engineer / Data Scientist
📧 [omkarkar006@gmail.com](mailto:omkarkar006@gmail.com)
🌐 [GitHub Profile](https://github.com/justmalto)

---
