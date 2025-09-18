import React, { useState, useEffect } from "react";
import "./Navbar.css";

function Navbar() {
  const [isRunning, setIsRunning] = useState(false);
  const [loading, setLoading] = useState(false);

  // ✅ Sync with backend status on first load and when polling
  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const res = await fetch("http://localhost:8000/status");
        const data = await res.json();
        setIsRunning(data.status === "processing"); // ✅ correct mapping
      } catch (err) {
        console.error("Error fetching status:", err);
      }
    };

    fetchStatus();

    // 🔄 Poll every 3s to stay in sync
    const interval = setInterval(fetchStatus, 3000);
    return () => clearInterval(interval);
  }, []);

  const handleStart = async () => {
    setLoading(true);
    try {
      const res = await fetch("http://localhost:8000/start", { method: "POST" });
      await res.json();
      setIsRunning(true); // optimistic update
    } catch (err) {
      console.error("Error starting generator:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleStop = async () => {
    setLoading(true);
    try {
      const res = await fetch("http://localhost:8000/stop", { method: "POST" });
      await res.json();
      setIsRunning(false); // optimistic update
    } catch (err) {
      console.error("Error stopping generator:", err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <nav className="navbar">
      <div className="navbar-title">Fraud Dashboard</div>
      <div className="navbar-buttons">
        <button
          className={`navbar-button ${isRunning ? "running" : ""}`}
          onClick={isRunning ? handleStop : handleStart}
          disabled={loading}
        >
          {loading ? "⏳" : isRunning ? "⏹ Stop" : "▶ Start"}
        </button>
      </div>
    </nav>
  );
}

export default Navbar;
