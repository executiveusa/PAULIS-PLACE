from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from models.base import Base, engine, get_db
from api import dashboard, products, tasks, approvals
from api import research_lab, payments, council, memory
from api import health as health_api
from api import voice as voice_api
from api import integrations as integrations_api
from api import printing_press as pp_api
from services import event_bus as event_bus_service
from agents import council_adversarial, voice_router, sssf
from services import zernio_service
from workers.tasks import scan_all_trends, score_hot_trends, create_products_from_trends
from workers.boot_task import boot_system
import json
import os
from datetime import datetime, timezone

# Wire Yappyverse event subscribers at import time (idempotent)
council_adversarial.register()
voice_router.register()
sssf.register_subscribers()
zernio_service.register()

# Create tables (best-effort: skip if DB unreachable in dev)
try:
    Base.metadata.create_all(bind=engine)
except Exception as _e:
    print(f"[main] db.create_all skipped (dev ok): {type(_e).__name__}")

app = FastAPI(title="Pauli's Place API", version="1.0.0")

# Exact-origin CORS. Additional origins can be supplied as a comma-separated
# PAULI_ALLOWED_ORIGINS value. Never use '*' with credentialed requests.
_default_origins = [
    "http://localhost:3000",
    "https://paulis-place.vercel.app",
]
_extra_origins = [
    origin.strip().rstrip("/")
    for origin in os.environ.get("PAULI_ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
]
_allowed_origins = list(dict.fromkeys(_default_origins + _extra_origins))

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Pauli-Approval", "X-Request-ID"],
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


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)


manager = ConnectionManager()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    origin = (websocket.headers.get("origin") or "").rstrip("/")
    if origin and origin not in _allowed_origins:
        await websocket.close(code=1008, reason="origin not allowed")
        return

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
    """Public liveness response. Never disclose infrastructure URLs or secrets."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_bus": "configured",
    }


@app.post("/api/trigger/boot")
def trigger_boot():
    task = boot_system.delay()
    return {"status": "queued", "task_id": task.id}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
