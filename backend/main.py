from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from models.base import Base, engine, get_db
from api import dashboard, products, tasks, approvals
from api import research_lab, payments, council, memory
from api import health as health_api
from api import voice as voice_api
from api import integrations as integrations_api
from api import control_plane as control_plane_api
from api import printing_press as pp_api
from services import hermes as hermes_service
from services import event_bus as event_bus_service
from agents import council_adversarial, voice_router, sssf
from services import zernio_service, ledger_service
from workers.tasks import scan_all_trends, score_hot_trends, create_products_from_trends
from workers.boot_task import boot_system
import json
from datetime import datetime, timezone
from config import SETTINGS

# Wire Yappyverse event subscribers at import time (idempotent)
council_adversarial.register()
voice_router.register()
sssf.register_subscribers()
zernio_service.register()

# Create legacy SQLAlchemy tables (best-effort for local dev). The canonical
# Pauli control plane is migrated separately in the `pauli` Supabase schema.
try:
    Base.metadata.create_all(bind=engine)
except Exception as _e:
    print(f"[main] db.create_all skipped (dev ok): {type(_e).__name__}")

app = FastAPI(
    title="Pauli's Place API",
    version="2.0.0",
    description="Voice-first autonomous business OS control plane and factory runtime.",
)

# CORS is configuration-driven rather than localhost-only.
_origins = [origin.strip() for origin in SETTINGS.allowed_origins.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])
app.include_router(products.router, prefix="/api/products", tags=["products"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])
app.include_router(approvals.router, prefix="/api/approvals", tags=["approvals"])
app.include_router(research_lab.router, tags=["research_lab"])
app.include_router(payments.router, tags=["payments"])
app.include_router(council.router, tags=["council"])
app.include_router(memory.router, tags=["memory"])
app.include_router(health_api.router, tags=["health"])
app.include_router(voice_api.router, tags=["voice"])
app.include_router(pp_api.router, tags=["printing-press"])
app.include_router(integrations_api.router)
app.include_router(control_plane_api.router)


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                pass


manager = ConnectionManager()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    event_bus_service.register_websocket(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "replay" and msg.get("event_id"):
                    env = event_bus_service.replay(msg["event_id"])
                    if env:
                        await websocket.send_json({"type": "replay", "envelope": env})
            except Exception:
                pass
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        event_bus_service.unregister_websocket(websocket)


@app.post("/api/trigger/scan-trends")
def trigger_trend_scan(db: Session = Depends(get_db)):
    task = scan_all_trends.delay()
    return {"status": "queued", "task_id": task.id}


@app.post("/api/trigger/score-trends")
def trigger_score_trends(db: Session = Depends(get_db)):
    task = score_hot_trends.delay()
    return {"status": "queued", "task_id": task.id}


@app.post("/api/trigger/create-products")
def trigger_product_creation(db: Session = Depends(get_db)):
    task = create_products_from_trends.delay()
    return {"status": "queued", "task_id": task.id}


@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "product": "Pauli's Place",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "broker": "redis" if "redis" in SETTINGS.redis_url else "custom",
    }


@app.post("/api/trigger/boot")
def trigger_boot():
    task = boot_system.delay()
    return {"status": "queued", "task_id": task.id}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
