import httpx

from app.config import settings
from app.models import SentimentData, SignalType


async def fetch_sentiment_data() -> SentimentData:
    data = SentimentData()
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(settings.fear_greed_url)
            if resp.status_code == 200:
                result = resp.json()
                entry = result["data"][0]
                data.fear_greed_index = int(entry["value"])
                data.fear_greed_label = entry["value_classification"]
        except Exception:
            return data

    # Contrarian logic: extreme fear = buy opportunity, extreme greed = sell signal
    if data.fear_greed_index is not None:
        idx = data.fear_greed_index
        if idx <= 20:
            data.signal = SignalType.STRONG_BUY
        elif idx <= 35:
            data.signal = SignalType.BUY
        elif idx >= 80:
            data.signal = SignalType.STRONG_SELL
        elif idx >= 65:
            data.signal = SignalType.SELL
        else:
            data.signal = SignalType.NEUTRAL

    return data
