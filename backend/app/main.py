from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.session import Base, engine, SessionLocal
from app.models import models  # noqa: F401
from app.api.routes import router
from app.services.water import ensure_defaults

app = FastAPI(title="Smart Hostel Water Monitoring API", version="1.0.0", description="Room-level water monitoring prototype")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_credentials=False, allow_methods=["*"], allow_headers=["*"])
app.include_router(router)

@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    db=SessionLocal()
    try: ensure_defaults(db)
    finally: db.close()

@app.get("/")
def root():
    return {"message":"Smart Hostel Water Monitoring API is running", "docs":"/docs", "room":"ROOM-101"}
