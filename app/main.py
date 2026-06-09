import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from app.api.routes import router
from app.api.websocket import broadcast_loop, websocket_endpoint
from app.services.binance_client import binance_client
from app.services.data_manager import data_manager

BASE_DIR = Path(__file__).resolve().parent.parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    task_dm = asyncio.create_task(data_manager.start())
    task_ws = asyncio.create_task(broadcast_loop())
    yield
    # Shutdown
    data_manager.stop()
    task_dm.cancel()
    task_ws.cancel()
    await binance_client.close()


app = FastAPI(title="BTC Signal Bot", version="1.0.0", lifespan=lifespan)
app.include_router(router)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

app.websocket("/ws")(websocket_endpoint)


@app.get("/")
async def dashboard(request: Request):
    return templates.TemplateResponse(request, "index.html")
