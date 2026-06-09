from datetime import datetime, timezone

import pandas as pd

from app.config import settings
from app.indicators.onchain import fetch_onchain_data
from app.indicators.sentiment import fetch_sentiment_data
from app.indicators.technical import calculate_indicators
from app.models import Indicator, SignalResult, SignalType


_SIGNAL_SCORES = {
    SignalType.STRONG_BUY: 1.0,
    SignalType.BUY: 0.5,
    SignalType.NEUTRAL: 0.0,
    SignalType.SELL: -0.5,
    SignalType.STRONG_SELL: -1.0,
}


def _score_indicators(indicators: list[Indicator]) -> float:
    if not indicators:
        return 0.0
    total = sum(_SIGNAL_SCORES[i.signal] for i in indicators)
    return total / len(indicators)


def _score_to_signal(score: float) -> SignalType:
    if score >= 0.4:
        return SignalType.STRONG_BUY
    if score >= 0.15:
        return SignalType.BUY
    if score <= -0.4:
        return SignalType.STRONG_SELL
    if score <= -0.15:
        return SignalType.SELL
    return SignalType.NEUTRAL


async def generate_signal(df: pd.DataFrame, timeframe: str) -> SignalResult:
    price = df["close"].iloc[-1]

    # Technical analysis
    indicators = calculate_indicators(df)
    tech_score = _score_indicators(indicators)

    # On-chain data
    onchain = await fetch_onchain_data()
    onchain_score = _SIGNAL_SCORES[onchain.signal]

    # Sentiment data
    sentiment = await fetch_sentiment_data()
    sentiment_score = _SIGNAL_SCORES[sentiment.signal]

    # Weighted aggregation
    final_score = (
        tech_score * settings.weight_technical
        + onchain_score * settings.weight_onchain
        + sentiment_score * settings.weight_sentiment
    )

    confidence = min(abs(final_score) * 100, 100)

    return SignalResult(
        timeframe=timeframe,
        timestamp=datetime.now(timezone.utc),
        price=price,
        signal=_score_to_signal(final_score),
        confidence=round(confidence, 1),
        technical_score=round(tech_score, 4),
        onchain_score=round(onchain_score, 4),
        sentiment_score=round(sentiment_score, 4),
        indicators=indicators,
        onchain=onchain,
        sentiment=sentiment,
    )
