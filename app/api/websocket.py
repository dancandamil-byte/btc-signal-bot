import asyncio
import json

from fastapi import WebSocket, WebSocketDisconnect

from app.config import settings
from app.services.data_manager import data_manager


class ConnectionManager:
    def __init__(self):
        self.connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.connections.append(ws)

    def disconnect(self, ws: WebSocket):
        self.connections.remove(ws)

    async def broadcast(self, data: dict):
        for ws in self.connections[:]:
            try:
                await ws.send_text(json.dumps(data, default=str))
            except Exception:
                self.connections.remove(ws)


manager = ConnectionManager()


async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(ws)


async def broadcast_loop():
    while True:
        signals = data_manager.get_all_signals()
        payload = {tf: s.model_dump() if s else None for tf, s in signals.items()}
        if manager.connections:
            await manager.broadcast(payload)
        await asyncio.sleep(settings.ws_broadcast_interval)
