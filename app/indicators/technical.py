import pandas as pd
import ta

from app.models import Indicator, SignalType


def _signal_from_score(score: float) -> SignalType:
    if score >= 0.6:
        return SignalType.STRONG_BUY
    if score >= 0.2:
        return SignalType.BUY
    if score <= -0.6:
        return SignalType.STRONG_SELL
    if score <= -0.2:
        return SignalType.SELL
    return SignalType.NEUTRAL


def calculate_indicators(df: pd.DataFrame) -> list[Indicator]:
    indicators = []
    c, h, l, v = df["close"], df["high"], df["low"], df["volume"]

    # RSI
    rsi = ta.momentum.RSIIndicator(c).rsi().iloc[-1]
    score = (30 - rsi) / 30 if rsi < 30 else (70 - rsi) / 30 if rsi > 70 else 0
    indicators.append(Indicator(name="RSI", value=round(rsi, 2), signal=_signal_from_score(score)))

    # MACD
    macd = ta.trend.MACD(c)
    macd_diff = macd.macd_diff().iloc[-1]
    score = 0.5 if macd_diff > 0 else -0.5
    indicators.append(Indicator(name="MACD", value=round(macd_diff, 4), signal=_signal_from_score(score)))

    # Bollinger Bands
    bb = ta.volatility.BollingerBands(c)
    bb_pct = bb.bollinger_pband().iloc[-1]
    score = (0.2 - bb_pct) * 2 if bb_pct < 0.2 else (bb_pct - 0.8) * -2 if bb_pct > 0.8 else 0
    indicators.append(Indicator(name="Bollinger Bands", value=round(bb_pct, 4), signal=_signal_from_score(score)))

    # EMA 9/21 Crossover
    ema9 = ta.trend.EMAIndicator(c, 9).ema_indicator().iloc[-1]
    ema21 = ta.trend.EMAIndicator(c, 21).ema_indicator().iloc[-1]
    score = 0.5 if ema9 > ema21 else -0.5
    indicators.append(Indicator(name="EMA 9/21", value=round(ema9 - ema21, 2), signal=_signal_from_score(score)))

    # EMA 50/200 (Golden/Death Cross)
    ema50 = ta.trend.EMAIndicator(c, 50).ema_indicator().iloc[-1]
    ema200 = ta.trend.EMAIndicator(c, 200).ema_indicator().iloc[-1]
    score = 0.7 if ema50 > ema200 else -0.7
    indicators.append(Indicator(name="EMA 50/200", value=round(ema50 - ema200, 2), signal=_signal_from_score(score)))

    # Stochastic
    stoch = ta.momentum.StochasticOscillator(h, l, c)
    stoch_k = stoch.stoch().iloc[-1]
    score = 0.5 if stoch_k < 20 else -0.5 if stoch_k > 80 else 0
    indicators.append(Indicator(name="Stochastic", value=round(stoch_k, 2), signal=_signal_from_score(score)))

    # ATR
    atr = ta.volatility.AverageTrueRange(h, l, c).average_true_range().iloc[-1]
    atr_pct = atr / c.iloc[-1] * 100
    indicators.append(Indicator(name="ATR", value=round(atr, 2), signal=SignalType.NEUTRAL))

    # ADX
    adx = ta.trend.ADXIndicator(h, l, c)
    adx_val = adx.adx().iloc[-1]
    plus_di = adx.adx_pos().iloc[-1]
    minus_di = adx.adx_neg().iloc[-1]
    score = 0 if adx_val < 25 else (0.5 if plus_di > minus_di else -0.5)
    indicators.append(Indicator(name="ADX", value=round(adx_val, 2), signal=_signal_from_score(score)))

    # Volume Analysis
    vol_sma = v.rolling(20).mean().iloc[-1]
    vol_ratio = v.iloc[-1] / vol_sma if vol_sma > 0 else 1
    price_change = c.iloc[-1] - c.iloc[-2]
    score = 0.3 if vol_ratio > 1.5 and price_change > 0 else -0.3 if vol_ratio > 1.5 and price_change < 0 else 0
    indicators.append(Indicator(name="Volume", value=round(vol_ratio, 2), signal=_signal_from_score(score)))

    # OBV
    obv = ta.volume.OnBalanceVolumeIndicator(c, v).on_balance_volume()
    obv_slope = obv.iloc[-1] - obv.iloc[-5]
    score = 0.3 if obv_slope > 0 else -0.3
    indicators.append(Indicator(name="OBV", value=round(obv.iloc[-1], 0), signal=_signal_from_score(score)))

    # Ichimoku Cloud
    ichi = ta.trend.IchimokuIndicator(h, l)
    span_a = ichi.ichimoku_a().iloc[-1]
    span_b = ichi.ichimoku_b().iloc[-1]
    price = c.iloc[-1]
    score = 0.5 if price > max(span_a, span_b) else -0.5 if price < min(span_a, span_b) else 0
    indicators.append(Indicator(name="Ichimoku", value=round(price - span_a, 2), signal=_signal_from_score(score)))

    # VWAP
    vwap = (v * (h + l + c) / 3).cumsum() / v.cumsum()
    vwap_val = vwap.iloc[-1]
    score = 0.3 if price > vwap_val else -0.3
    indicators.append(Indicator(name="VWAP", value=round(vwap_val, 2), signal=_signal_from_score(score)))

    # Williams %R
    wr = ta.momentum.WilliamsRIndicator(h, l, c).williams_r().iloc[-1]
    score = 0.5 if wr < -80 else -0.5 if wr > -20 else 0
    indicators.append(Indicator(name="Williams %R", value=round(wr, 2), signal=_signal_from_score(score)))

    # CCI
    cci = ta.trend.CCIIndicator(h, l, c).cci().iloc[-1]
    score = -0.5 if cci > 100 else 0.5 if cci < -100 else 0
    indicators.append(Indicator(name="CCI", value=round(cci, 2), signal=_signal_from_score(score)))

    # Parabolic SAR
    psar = ta.trend.PSARIndicator(h, l, c)
    psar_up = psar.psar_up().iloc[-1]
    psar_down = psar.psar_down().iloc[-1]
    is_bullish = pd.notna(psar_up)
    score = 0.4 if is_bullish else -0.4
    indicators.append(Indicator(name="Parabolic SAR", value=round(psar_up if is_bullish else psar_down, 2), signal=_signal_from_score(score)))

    # Supertrend (ATR-based approximation)
    atr14 = ta.volatility.AverageTrueRange(h, l, c, 14).average_true_range()
    hl2 = (h + l) / 2
    upper = hl2 + 3 * atr14
    lower = hl2 - 3 * atr14
    supertrend_bull = c.iloc[-1] > lower.iloc[-1]
    score = 0.4 if supertrend_bull else -0.4
    indicators.append(Indicator(name="Supertrend", value=round(lower.iloc[-1] if supertrend_bull else upper.iloc[-1], 2), signal=_signal_from_score(score)))

    return indicators
