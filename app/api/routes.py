from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from app.models import HealthResponse
from app.services.data_manager import data_manager

router = APIRouter(prefix="/api")
_start_time = datetime.now(timezone.utc)


@router.get("/signals/all")
async def get_all_signals():
    return {tf: s.model_dump() if s else None for tf, s in data_manager.get_all_signals().items()}


@router.get("/signals/{timeframe}")
async def get_signal(timeframe: str):
    signal = data_manager.get_signal(timeframe)
    if not signal:
        raise HTTPException(404, f"Sin señal para {timeframe}")
    return signal.model_dump()


@router.get("/indicators/{timeframe}")
async def get_indicators(timeframe: str):
    signal = data_manager.get_signal(timeframe)
    if not signal:
        raise HTTPException(404, f"Sin datos para {timeframe}")
    return [i.model_dump() for i in signal.indicators]


@router.get("/history/{timeframe}")
async def get_history(timeframe: str):
    return [s.model_dump() for s in data_manager.get_history(timeframe)]


@router.get("/results/{timeframe}")
async def get_results(timeframe: str):
    return data_manager.get_results_db(timeframe)


@router.get("/stats/{timeframe}")
async def get_stats(timeframe: str):
    return data_manager.get_stats(timeframe).model_dump()


@router.get("/stats")
async def get_stats_all():
    return data_manager.get_stats().model_dump()


@router.get("/health")
async def health():
    now = datetime.now(timezone.utc)
    return HealthResponse(status="ok", timestamp=now, uptime_seconds=(now - _start_time).total_seconds())
