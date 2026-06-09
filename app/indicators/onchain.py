import httpx

from app.config import settings
from app.models import OnChainData, SignalType


async def fetch_onchain_data() -> OnChainData:
    data = OnChainData()
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            # Hashrate trend from blockchain.info
            resp = await client.get(f"{settings.blockchain_info_url}/q/hashrate")
            if resp.status_code == 200:
                current_hr = float(resp.text)
                data.hashrate_trend = "increasing" if current_hr > 0 else "stable"
        except Exception:
            pass

        try:
            # Estimated fees from mempool.space
            resp = await client.get(f"{settings.mempool_url}/fees/recommended")
            if resp.status_code == 200:
                fees = resp.json()
                data.estimated_fees = fees.get("halfHourFee", 0)
        except Exception:
            pass

        try:
            # Difficulty adjustment from mempool.space
            resp = await client.get(f"{settings.mempool_url}/difficulty-adjustment")
            if resp.status_code == 200:
                adj = resp.json()
                data.difficulty_adjustment = adj.get("difficultyChange", 0)
        except Exception:
            pass

    # Generate signal: rising hashrate + positive difficulty = bullish
    score = 0
    if data.hashrate_trend == "increasing":
        score += 0.3
    if data.difficulty_adjustment and data.difficulty_adjustment > 0:
        score += 0.3
    if data.estimated_fees and data.estimated_fees > 50:
        score += 0.2  # High fees = high network demand

    if score >= 0.5:
        data.signal = SignalType.BUY
    elif score <= -0.3:
        data.signal = SignalType.SELL
    else:
        data.signal = SignalType.NEUTRAL

    return data
