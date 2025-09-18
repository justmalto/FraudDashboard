import React, { useEffect, useState, useRef } from "react";
import "./LiveAlertPanel.css";

function LiveAlertPanel() {
  const [transactions, setTransactions] = useState([]);
  const [showHighAlerts, setShowHighAlerts] = useState(false);
  const [status, setStatus] = useState("disconnected"); // connected | reconnecting | error
  const wsRef = useRef(null);
  const retryRef = useRef(1000); // retry delay in ms

  const connectWS = () => {
    setStatus("reconnecting");
    const ws = new WebSocket("ws://localhost:8000/ws/alerts");
    wsRef.current = ws;

    ws.onopen = () => {
      console.log("✅ WebSocket connected");
      setStatus("connected");
      retryRef.current = 1000; // reset backoff
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (!data.transaction) return;

        setTransactions((prev) => {
          const updated = [data.transaction, ...prev];
          return updated.slice(0, 10); // keep last 10
        });
      } catch (err) {
        console.error("❌ Failed to parse message", err);
      }
    };

    ws.onerror = (err) => {
      console.error("❌ WebSocket error", err);
      setStatus("error");
      ws.close();
    };

    ws.onclose = () => {
      console.warn("⚠️ WebSocket closed. Retrying...");
      setStatus("reconnecting");
      setTimeout(() => {
        retryRef.current = Math.min(retryRef.current * 2, 30000); // max 30s
        connectWS();
      }, retryRef.current);
    };
  };

  useEffect(() => {
    connectWS();
    return () => wsRef.current?.close();
  }, []);

  const filteredTxns = showHighAlerts
    ? transactions.filter((t) => t.risk_score >= 0.8)
    : transactions;

  return (
    <div className="alert-panel">
      <div className="alert-panel-header">
        <h2>Live Alerts</h2>
        <div className={`status ${status}`}>Status: {status}</div>
        <button
          className={`toggle-btn ${showHighAlerts ? "active" : ""}`}
          onClick={() => setShowHighAlerts(!showHighAlerts)}
        >
          {showHighAlerts ? "Show All" : "High Alerts Only"}
        </button>
      </div>

      <div className="alert-panel-tablecontainer">
        <table className="alert-table">
          <thead>
            <tr>
              <th>Distance from Home</th>
              <th>Distance from Last Txn</th>
              <th>Differential Purchase Ratio</th>
              <th>Repeat Retailer</th>
              <th>Used Chip</th>
              <th>Used PIN</th>
              <th>Online Order</th>
              <th>Risk Score</th>
              <th>Timestamp</th>
            </tr>
          </thead>
          <tbody>
            {filteredTxns.map((txn, idx) => (
              <tr
                key={idx}
                className={txn.risk_score >= 0.8 ? "high-risk" : ""}
              >
                <td>{txn.distance_from_home?.toFixed(2)}</td>
                <td>{txn.distance_from_last_transaction?.toFixed(2)}</td>
                <td>{txn.ratio_to_median_purchase_price?.toFixed(2)}</td>
                <td>{txn.repeat_retailer ? "Yes" : "No"}</td>
                <td>{txn.used_chip ? "Yes" : "No"}</td>
                <td>{txn.used_pin_number ? "Yes" : "No"}</td>
                <td>{txn.online_order ? "Yes" : "No"}</td>
                <td>{txn.risk_score?.toFixed(2)}</td>
                <td>{txn.timestamp}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default LiveAlertPanel;
