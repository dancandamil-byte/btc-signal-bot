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
    hashrate_trend: str = "unknown"
    estimated_fees: float | None = None
    difficulty_adjustment: float | None = None
    signal: SignalType = SignalType.NEUTRAL


class SentimentData(BaseModel):
    fear_greed_index: int | None = None
    fear_greed_label: str = "unknown"
    signal: SignalType = SignalType.NEUTRAL


class SignalResult(BaseModel):
    timeframe: str
    timestamp: datetime
    price: float
    signal: SignalType
    confidence: float
    technical_score: float
    onchain_score: float
    sentiment_score: float
    indicators: list[Indicator] = []
    onchain: OnChainData = OnChainData()
    sentiment: SentimentData = SentimentData()


class HealthResponse(BaseModel):
    status: str = "ok"
    timestamp: datetime
    uptime_seconds: float
