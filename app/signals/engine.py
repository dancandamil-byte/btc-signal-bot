from datetime import datetime, timezone

import pandas as pd
import ta

from app.config import settings
from app.indicators.onchain import fetch_onchain_data
from app.indicators.sentiment import fetch_sentiment_data
from app.indicators.technical import calculate_indicators
from app.models import Indicator, SignalResult, SignalType, TradeSetup


_SIGNAL_SCORES = {
    SignalType.STRONG_BUY: 1.0,
    SignalType.BUY: 0.5,
    SignalType.NEUTRAL: 0.0,
    SignalType.SELL: -0.5,
    SignalType.STRONG_SELL: -1.0,
}

_SIGNAL_ESPANOL = {
    SignalType.STRONG_BUY: "🟢 COMPRA FUERTE",
    SignalType.BUY: "🟢 COMPRAR",
    SignalType.NEUTRAL: "🟡 NEUTRAL",
    SignalType.SELL: "🔴 VENDER",
    SignalType.STRONG_SELL: "🔴 VENTA FUERTE",
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


def _calculate_trade_setup(df: pd.DataFrame, signal: SignalType, price: float) -> TradeSetup | None:
    if signal == SignalType.NEUTRAL:
        return None

    atr = ta.volatility.AverageTrueRange(df["high"], df["low"], df["close"], window=14).average_true_range().iloc[-1]
    spread = atr * 0.3

    is_buy = signal in (SignalType.BUY, SignalType.STRONG_BUY)

    if is_buy:
        entry_min = round(price - spread, 0)
        entry_max = round(price + spread, 0)
        tp1 = round(price + atr * 1, 0)
        tp2 = round(price + atr * 2, 0)
        tp3 = round(price + atr * 3, 0)
        tp4 = round(price + atr * 4, 0)
        tp5 = round(price + atr * 5, 0)
        sl = round(price - atr * 2, 0)
    else:
        entry_min = round(price - spread, 0)
        entry_max = round(price + spread, 0)
        tp1 = round(price - atr * 1, 0)
        tp2 = round(price - atr * 2, 0)
        tp3 = round(price - atr * 3, 0)
        tp4 = round(price - atr * 4, 0)
        tp5 = round(price - atr * 5, 0)
        sl = round(price + atr * 2, 0)

    return TradeSetup(
        entry_min=entry_min, entry_max=entry_max,
        tp1=tp1, tp2=tp2, tp3=tp3, tp4=tp4, tp5=tp5, sl=sl,
    )


def _generate_mensaje(signal: SignalType, price: float, setup: TradeSetup | None, confidence: float, timeframe: str) -> str:
    if signal == SignalType.NEUTRAL:
        return f"⏸️ BTC Sin señal clara | Precio: ${price:,.0f} | TF: {timeframe} | Confianza: {confidence}%"

    accion = _SIGNAL_ESPANOL[signal]
    msg = f"""━━━━━━━━━━━━━━━━━━━━━
{accion} | BTC/USDT
━━━━━━━━━━━━━━━━━━━━━
📍 Entrada: ${setup.entry_min:,.0f} / ${setup.entry_max:,.0f}

🎯 TP1: ${setup.tp1:,.0f}
🎯 TP2: ${setup.tp2:,.0f}
🎯 TP3: ${setup.tp3:,.0f}
🎯 TP4: ${setup.tp4:,.0f}
🎯 TP5: ${setup.tp5:,.0f}

🛑 SL: ${setup.sl:,.0f}

⏱️ Timeframe: {timeframe}
📊 Confianza: {confidence}%
━━━━━━━━━━━━━━━━━━━━━"""
    return msg


async def generate_signal(df: pd.DataFrame, timeframe: str) -> SignalResult:
    price = df["close"].iloc[-1]

    indicators = calculate_indicators(df)
    tech_score = _score_indicators(indicators)

    onchain = await fetch_onchain_data()
    onchain_score = _SIGNAL_SCORES[onchain.signal]

    sentiment = await fetch_sentiment_data()
    sentiment_score = _SIGNAL_SCORES[sentiment.signal]

    final_score = (
        tech_score * settings.weight_technical
        + onchain_score * settings.weight_onchain
        + sentiment_score * settings.weight_sentiment
    )

    confidence = min(abs(final_score) * 100, 100)
    signal = _score_to_signal(final_score)
    trade_setup = _calculate_trade_setup(df, signal, price)
    mensaje = _generate_mensaje(signal, price, trade_setup, round(confidence, 1), timeframe)

    return SignalResult(
        timeframe=timeframe,
        timestamp=datetime.now(timezone.utc),
        price=price,
        signal=signal,
        confidence=round(confidence, 1),
        technical_score=round(tech_score, 4),
        onchain_score=round(onchain_score, 4),
        sentiment_score=round(sentiment_score, 4),
        trade_setup=trade_setup,
        mensaje=mensaje,
        indicators=indicators,
        onchain=onchain,
        sentiment=sentiment,
    )
