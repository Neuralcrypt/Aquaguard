import pandas as pd

def prepare_readings(rows):
    """Normalize reading records and derive basic time features."""
    df = pd.DataFrame(rows)
    required = {"timestamp", "interval_volume_litres", "flow_rate_lpm"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
    df["interval_volume_litres"] = pd.to_numeric(df["interval_volume_litres"], errors="coerce")
    df["flow_rate_lpm"] = pd.to_numeric(df["flow_rate_lpm"], errors="coerce")
    df = df.dropna(subset=["timestamp", "interval_volume_litres", "flow_rate_lpm"])
    df = df[(df["interval_volume_litres"] >= 0) & (df["flow_rate_lpm"] >= 0)].copy()
    df["hour"] = df["timestamp"].dt.hour
    df["month"] = df["timestamp"].dt.month
    return df
