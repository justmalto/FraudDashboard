import React, { useEffect, useState, useRef } from "react";
import {
  Chart as ChartJS,
  ArcElement,
  Tooltip,
  Legend,
  CategoryScale,
  LinearScale,
  BarElement,
} from "chart.js";
import { Pie, Bar } from "react-chartjs-2";
import "./Analytics.css";

ChartJS.register(ArcElement, Tooltip, Legend, CategoryScale, LinearScale, BarElement);

const COLORS = ["#7171beff", "#000052"]; // fraud, safe

function Analytics() {
  const [fraudData, setFraudData] = useState(null);
  const [histograms, setHistograms] = useState({
    distance_from_home_hist: null,
    distance_from_last_transaction_hist: null,
    purchase_ratio_hist: null,
  });

  const wsRef = useRef(null);
  const retryRef = useRef(0);

  // Chart refs to update data smoothly
  const pieRef = useRef(null);
  const histRefs = {
    distance_from_home_hist: useRef(null),
    distance_from_last_transaction_hist: useRef(null),
    purchase_ratio_hist: useRef(null),
  };

  useEffect(() => {
    let retryTimeout;

    const connect = () => {
      wsRef.current = new WebSocket("ws://localhost:8000/ws/analytics");

      wsRef.current.onopen = () => {
        console.log("✅ WebSocket connected");
        retryRef.current = 0;
      };

      wsRef.current.onmessage = (event) => {
        const data = JSON.parse(event.data);

        // Update Pie chart smoothly
        if (pieRef.current) {
          pieRef.current.data.datasets[0].data = [
            data.fraud_count || 0,
            data.safe_count || 0,
          ];
          pieRef.current.update();
        } else {
          setFraudData({
            labels: ["Fraud", "Safe"],
            datasets: [
              {
                data: [data.fraud_count || 0, data.safe_count || 0],
                backgroundColor: COLORS,
              }],
          });
        }

        // Update histograms smoothly
        const formatHistogram = (hist) =>
          hist?.map((item) => ({
            bin: item.bin,
            fraud: item.fraud || 0,
            safe: item.safe || 0,
          })) || [];

        const newHist = {
          distance_from_home_hist: formatHistogram(data.distance_from_home_hist),
          distance_from_last_transaction_hist: formatHistogram(
            data.distance_from_last_transaction_hist
          ),
          purchase_ratio_hist: formatHistogram(data.purchase_ratio_hist),
        };

        Object.keys(newHist).forEach((key) => {
          if (histRefs[key].current && newHist[key].length) {
            histRefs[key].current.data.labels = newHist[key].map((d) => d.bin);
            histRefs[key].current.data.datasets[0].data = newHist[key].map((d) => d.fraud);
            histRefs[key].current.data.datasets[1].data = newHist[key].map((d) => d.safe);
            histRefs[key].current.update();
          }
        });

        setHistograms(newHist);
      };

      wsRef.current.onerror = (err) => {
        console.error("❌ WebSocket error:", err);
        wsRef.current.close();
      };

      wsRef.current.onclose = () => {
        console.warn("⚠️ WebSocket closed, retrying...");
        const delay = Math.min(10000, 1000 * 2 ** retryRef.current);
        retryRef.current += 1;
        retryTimeout = setTimeout(connect, delay);
      };
    };

    connect();

    return () => {
      clearTimeout(retryTimeout);
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  const renderHistogram = (data, title, refKey) => {
    if (!data || data.length === 0)
      return (
        <div className="analytics-card">
          <h2 className="analytics-title">{title}</h2>
          <div className="loading">Loading...</div>
        </div>
      );

    const barData = {
      labels: data.map((d) => d.bin),
      datasets: [
        {
          label: "Fraud",
          data: data.map((d) => d.fraud),
          backgroundColor: "#7171beff",
        },
        {
          label: "Safe",
          data: data.map((d) => d.safe),
          backgroundColor: "#000052",
        },
      ],
    };

    const options = {
      responsive: true,
      plugins: { legend: { position: "top" }, tooltip: { mode: "index" } },
      scales: {
        x: { title: { display: true, text: "Bin" } },
        y: { title: { display: true, text: "Count" }, beginAtZero: true },
      },
    };

    return (
      <div className="analytics-card">
        <h2 className="analytics-title">{title}</h2>
        <Bar ref={histRefs[refKey]} data={barData} options={options} />
      </div>
    );
  };

  return (
    <div className="analytics-container">
      <div className="analytics-card">
        <h2 className="analytics-title">Fraud vs Safe Transactions</h2>
        {!fraudData ? <div className="loading">Loading...</div> : <div className="pie-container"><Pie ref={pieRef} 
        data={fraudData} /> </div>}
      </div>

      {renderHistogram(histograms.distance_from_home_hist, "Distance from Home vs Fraud/Safe", "distance_from_home_hist")}
      {renderHistogram(histograms.distance_from_last_transaction_hist, "Distance from Last Transaction vs Fraud/Safe", "distance_from_last_transaction_hist")}
      {renderHistogram(histograms.purchase_ratio_hist, "Purchase Ratio vs Fraud/Safe", "purchase_ratio_hist")}
    </div>
  );
}

export default Analytics;
