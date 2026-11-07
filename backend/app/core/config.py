import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./water_monitoring.db")
ROOM_ID = os.getenv("ROOM_ID", "ROOM-101")
