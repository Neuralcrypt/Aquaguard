
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.auth_routes import router as auth_router
from app.db.session import Base, engine, SessionLocal
from app.models import models  # noqa: F401
from app.models import auth  # noqa: F401
from app.api.routes import router
from app.db.migrations import migrate_hostel_data
from app.services.water import ensure_defaults
from app.services.auth import ensure_admin_exists
from app.api.admin_routes import router as admin_router


app = FastAPI(
    title="Smart Hostel Water Monitoring API",
    version="1.0.0",
    description="Room-level water monitoring prototype",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(auth_router)
app.include_router(admin_router)

@app.on_event("startup")
def startup():
    # Create missing tables without deleting existing database data.
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:
        # Create/find Bamashah Hostel and assign legacy rooms.
        hostel_id = migrate_hostel_data(db)

        # Ensure default room, sensor and seasonal settings exist.
        ensure_defaults(db, hostel_id=hostel_id)

        # Create the initial admin account if it doesn't exist.
        ensure_admin_exists(db)

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


@app.get("/")
def root():
    return {
        "message": "Smart Hostel Water Monitoring API is running",
        "docs": "/docs",
        "room": "ROOM-101",
    }
