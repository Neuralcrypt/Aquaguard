from src.anomaly_detector import detect_anomalies

def test_insufficient_data():
    assert detect_anomalies([1,2,3])["status"] == "insufficient_data"

def test_baseline_flags_extreme_value():
    result = detect_anomalies([1]*10 + [100])
    assert result["status"] == "complete"
    assert result["results"][-1]["is_anomaly"] is True
