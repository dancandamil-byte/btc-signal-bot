from datetime import datetime
from enum import Enum
from pydantic import BaseModel


class SignalType(str, Enum):
    STRONG_BUY = "STRONG_BUY"
    BUY = "BUY"
    NEUTRAL = "NEUTRAL"
    SELL = "SELL"
    STRONG_SELL = "STRONG_SELL"


class Indicator(BaseModel):
    name: str
    value: float | None = None
    signal: SignalType = SignalType.NEUTRAL
    weight: float = 1.0


class OnChainData(BaseModel):
    hashrate_trend: str = "desconocido"
    estimated_fees: float | None = None
    difficulty_adjustment: float | None = None
    signal: SignalType = SignalType.NEUTRAL


class SentimentData(BaseModel):
    fear_greed_index: int | None = None
    fear_greed_label: str = "desconocido"
    signal: SignalType = SignalType.NEUTRAL


class TradeSetup(BaseModel):
    entry_min: float
    entry_max: float
    tp1: float
    tp2: float
    tp3: float
    tp4: float
    tp5: float
    sl: float


class TradeResult(str, Enum):
    PENDIENTE = "PENDIENTE"
    TP1_ALCANZADO = "TP1_ALCANZADO"
    TP2_ALCANZADO = "TP2_ALCANZADO"
    TP3_ALCANZADO = "TP3_ALCANZADO"
    TP4_ALCANZADO = "TP4_ALCANZADO"
    TP5_ALCANZADO = "TP5_ALCANZADO"
    SL_ALCANZADO = "SL_ALCANZADO"


class SignalResult(BaseModel):
    timeframe: str
    timestamp: datetime
    price: float
    signal: SignalType
    confidence: float
    technical_score: float
    onchain_score: float
    sentiment_score: float
    trade_setup: TradeSetup | None = None
    mensaje: str = ""
    resultado: TradeResult = TradeResult.PENDIENTE
    indicators: list[Indicator] = []
    onchain: OnChainData = OnChainData()
    sentiment: SentimentData = SentimentData()


class HealthResponse(BaseModel):
    status: str = "ok"
    timestamp: datetime
    uptime_seconds: float
