import httpx

from app.config import settings
from app.models import OnChainData, SignalType


async def fetch_onchain_data() -> OnChainData:
    data = OnChainData()
    async with httpx.AsyncClient(timeout=10) as client:
        # Hashrate + dificultad
        try:
            resp = await client.get(f"{settings.blockchain_info_url}/q/hashrate")
            if resp.status_code == 200:
                data.hashrate_trend = "subiendo" if float(resp.text) > 0 else "estable"
        except Exception:
            pass

        try:
            resp = await client.get(f"{settings.mempool_url}/fees/recommended")
            if resp.status_code == 200:
                data.estimated_fees = resp.json().get("halfHourFee", 0)
        except Exception:
            pass

        try:
            resp = await client.get(f"{settings.mempool_url}/difficulty-adjustment")
            if resp.status_code == 200:
                data.difficulty_adjustment = resp.json().get("difficultyChange", 0)
        except Exception:
            pass

        # Funding rate (Binance public)
        try:
            resp = await client.get("https://fapi.binance.com/fapi/v1/fundingRate",
                                    params={"symbol": "BTCUSDT", "limit": 1})
            if resp.status_code == 200:
                fr = float(resp.json()[0]["fundingRate"])
                data.funding_rate = round(fr * 100, 4)
        except Exception:
            pass

        # Liquidaciones 24h (Coinglass proxy - public endpoint)
        try:
            resp = await client.get("https://open-api.coinglass.com/public/v2/liquidation/info",
                                    params={"symbol": "BTC", "timeType": 2})
            if resp.status_code == 200 and resp.json().get("data"):
                liq_data = resp.json()["data"]
                data.liquidations_24h = liq_data.get("totalVolUsd", 0)
        except Exception:
            pass

        # BTC Dominancia (CoinGecko public)
        try:
            resp = await client.get("https://api.coingecko.com/api/v3/global")
            if resp.status_code == 200:
                data.btc_dominance = resp.json()["data"]["market_cap_percentage"]["btc"]
        except Exception:
            pass

    # Scoring
    score = 0
    if data.hashrate_trend == "subiendo":
        score += 0.2
    if data.difficulty_adjustment and data.difficulty_adjustment > 0:
        score += 0.2
    if data.estimated_fees and data.estimated_fees > 50:
        score += 0.1

    # Funding rate: muy positivo = sobreapalancamiento long = bearish
    if data.funding_rate is not None:
        if data.funding_rate > 0.05:
            score -= 0.3
        elif data.funding_rate < -0.02:
            score += 0.3

    # Dominancia subiendo = BTC fuerte
    if data.btc_dominance and data.btc_dominance > 55:
        score += 0.1

    if score >= 0.4:
        data.signal = SignalType.BUY
    elif score <= -0.2:
        data.signal = SignalType.SELL
    else:
        data.signal = SignalType.NEUTRAL

    return data
