from statistics import median

def detect_anomalies(values, threshold=3.5):
    """Robust MAD baseline. This is a teaching baseline, not leak confirmation."""
    clean = [float(v) for v in values if v is not None and float(v) >= 0]
    if len(clean) < 10:
        return {"status":"insufficient_data", "minimum_readings":10, "results":[]}
    center = median(clean)
    mad = median([abs(v-center) for v in clean])
    results=[]
    for value in clean:
        score = abs(value-center)/(1.4826*mad) if mad else (0.0 if value == center else 99.0)
        results.append({"value":value, "score":score, "is_anomaly":score >= threshold})
    return {"status":"complete", "method":"robust-median-MAD", "results":results}
