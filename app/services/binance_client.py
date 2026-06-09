import ccxt.async_support as ccxt
import pandas as pd

from app.config import settings


class BinanceClient:
    def __init__(self):
        self.exchange = ccxt.binance({"enableRateLimit": True})

    async def fetch_ohlcv(self, timeframe: str) -> pd.DataFrame:
        data = await self.exchange.fetch_ohlcv(
            settings.symbol, timeframe, limit=settings.candle_limit
        )
        df = pd.DataFrame(data, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        return df

    async def get_price(self) -> float:
        ticker = await self.exchange.fetch_ticker(settings.symbol)
        return ticker["last"]

    async def close(self):
        await self.exchange.close()


binance_client = BinanceClient()
