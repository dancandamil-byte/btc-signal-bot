import asyncio
from collections import deque
from datetime import datetime, timezone

from app.config import settings
from app.models import SignalResult
from app.services.binance_client import binance_client
from app.signals.engine import generate_signal


class DataManager:
    def __init__(self):
        self.signals: dict[str, SignalResult | None] = {tf: None for tf in settings.timeframes}
        self.history: dict[str, deque] = {tf: deque(maxlen=100) for tf in settings.timeframes}
        self._running = False

    async def update_all(self):
        for tf in settings.timeframes:
            try:
                df = await binance_client.fetch_ohlcv(tf)
                signal = await generate_signal(df, tf)
                self.signals[tf] = signal
                self.history[tf].append(signal)
            except Exception as e:
                print(f"[DataManager] Error updating {tf}: {e}")

    async def start(self):
        self._running = True
        while self._running:
            await self.update_all()
            await asyncio.sleep(settings.update_interval)

    def stop(self):
        self._running = False

    def get_signal(self, timeframe: str) -> SignalResult | None:
        return self.signals.get(timeframe)

    def get_all_signals(self) -> dict[str, SignalResult | None]:
        return self.signals

    def get_history(self, timeframe: str) -> list[SignalResult]:
        return list(self.history.get(timeframe, []))


data_manager = DataManager()
