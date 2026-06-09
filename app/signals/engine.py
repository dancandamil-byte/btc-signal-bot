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


def _confluence_check(indicators: list[Indicator]) -> tuple[float, str]:
    """Calcula % de confluencia. Retorna (ratio, dirección)."""
    buys = sum(1 for i in indicators if i.signal in (SignalType.BUY, SignalType.STRONG_BUY))
    sells = sum(1 for i in indicators if i.signal in (SignalType.SELL, SignalType.STRONG_SELL))
    total = len(indicators)
    if total == 0:
        return 0.0, "neutral"
    buy_ratio = buys / total
    sell_ratio = sells / total
    if buy_ratio >= sell_ratio:
        return buy_ratio, "buy"
    return sell_ratio, "sell"


def _get_session(hour_utc: int) -> str:
    """Determina la sesión de trading actual."""
    for name, hours in settings.sessions.items():
        if hour_utc in hours:
            return name
    return "fuera_horario"


def _is_low_liquidity(hour_utc: int) -> bool:
    return hour_utc in settings.low_liquidity_hours


def _volatility_filter(df: pd.DataFrame) -> tuple[bool, float]:
    """Retorna (demasiado_volatil, atr_ratio)."""
    atr = ta.volatility.AverageTrueRange(df["high"], df["low"], df["close"], window=14).average_true_range()
    current_atr = atr.iloc[-1]
    avg_atr = atr.rolling(50).mean().iloc[-1]
    ratio = current_atr / avg_atr if avg_atr > 0 else 1.0
    return ratio > settings.max_atr_multiplier, ratio


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


def _generate_mensaje(signal: SignalType, price: float, setup: TradeSetup | None,
                       confidence: float, timeframe: str, confluence: float,
                       session: str, volatility_ratio: float, filtered: str | None) -> str:
    if filtered:
        return f"⚠️ Señal filtrada: {filtered}\n📍 Precio: ${price:,.0f} | TF: {timeframe}"

    if signal == SignalType.NEUTRAL:
        return f"⏸️ BTC Sin señal clara | ${price:,.0f} | TF: {timeframe} | Confluencia: {confluence:.0%}"

    accion = _SIGNAL_ESPANOL[signal]
    session_map = {"asia": "🌏 Asia", "europa": "🌍 Europa", "ny": "🌎 Nueva York", "fuera_horario": "⚠️ Fuera horario"}
    return f"""━━━━━━━━━━━━━━━━━━━━━
{accion} | BTC/USDT
━━━━━━━━━━━━━━━━━━━━━
📍 Entrada: ${setup.entry_min:,.0f} / ${setup.entry_max:,.0f}

🎯 TP1: ${setup.tp1:,.0f}
🎯 TP2: ${setup.tp2:,.0f}
🎯 TP3: ${setup.tp3:,.0f}
🎯 TP4: ${setup.tp4:,.0f}
🎯 TP5: ${setup.tp5:,.0f}

🛑 SL: ${setup.sl:,.0f}

⏱️ TF: {timeframe} | {session_map.get(session, session)}
📊 Confianza: {confidence:.1f}%
🔗 Confluencia: {confluence:.0%}
📈 Volatilidad: {volatility_ratio:.1f}x
━━━━━━━━━━━━━━━━━━━━━"""


async def generate_signal(df: pd.DataFrame, timeframe: str) -> SignalResult:
    price = df["close"].iloc[-1]
    now = datetime.now(timezone.utc)
    hour_utc = now.hour
    session = _get_session(hour_utc)

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
    raw_signal = _score_to_signal(final_score)

    # Filtros
    confluence_ratio, confluence_dir = _confluence_check(indicators)
    too_volatile, vol_ratio = _volatility_filter(df)
    low_liq = _is_low_liquidity(hour_utc)

    filtered = None
    signal = raw_signal

    if raw_signal != SignalType.NEUTRAL:
        if confluence_ratio < settings.confluence_threshold:
            filtered = f"Confluencia baja ({confluence_ratio:.0%} < {settings.confluence_threshold:.0%})"
            signal = SignalType.NEUTRAL
        elif too_volatile:
            filtered = f"Volatilidad extrema ({vol_ratio:.1f}x promedio)"
            signal = SignalType.NEUTRAL
        elif low_liq and settings.session_filter_enabled:
            filtered = f"Baja liquidez (hora UTC {hour_utc})"
            signal = SignalType.NEUTRAL

    trade_setup = _calculate_trade_setup(df, signal, price)
    mensaje = _generate_mensaje(signal, price, trade_setup, confidence, timeframe,
                                 confluence_ratio, session, vol_ratio, filtered)

    return SignalResult(
        timeframe=timeframe,
        timestamp=now,
        price=price,
        signal=signal,
        confidence=round(confidence, 1),
        technical_score=round(tech_score, 4),
        onchain_score=round(onchain_score, 4),
        sentiment_score=round(sentiment_score, 4),
        trade_setup=trade_setup,
        mensaje=mensaje,
        confluence=round(confluence_ratio, 4),
        session=session,
        volatility_ratio=round(vol_ratio, 2),
        filtered_reason=filtered,
        indicators=indicators,
        onchain=onchain,
        sentiment=sentiment,
    )
