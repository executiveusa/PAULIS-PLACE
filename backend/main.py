from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from models.base import Base, engine, get_db
from models.product import Product, ProductStatus
from models.task import Task, TaskStatus
from models.trend import Trend
from models.research import NicheInsight
from api import dashboard, products, tasks, approvals
from workers.tasks import scan_all_trends, score_hot_trends, create_products_from_trends
import json
from datetime import datetime, timezone

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="DigiFactory API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])
app.include_router(products.router, prefix="/api/products", tags=["products"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])
app.include_router(approvals.router, prefix="/api/approvals", tags=["approvals"])

# WebSocket for real-time updates
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass

manager = ConnectionManager()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle any client messages if needed
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# Manual triggers
@app.post("/api/trigger/scan-trends")
def trigger_trend_scan(db: Session = Depends(get_db)):
    """Manually trigger a trend scan"""
    task = scan_all_trends.delay()
    return {"status": "queued", "task_id": task.id}


@app.post("/api/trigger/score-trends")
def trigger_score_trends(db: Session = Depends(get_db)):
    """Manually trigger trend scoring"""
    task = score_hot_trends.delay()
    return {"status": "queued", "task_id": task.id}


@app.post("/api/trigger/create-products")
def trigger_product_creation(db: Session = Depends(get_db)):
    """Manually trigger product creation from trends"""
    task = create_products_from_trends.delay()
    return {"status": "queued", "task_id": task.id}


@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
