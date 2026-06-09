import asyncio
from collections import deque

from app.config import settings
from app.models import SignalResult, SignalType, TradeResult
from app.services.binance_client import binance_client
from app.signals.engine import generate_signal


class DataManager:
    def __init__(self):
        self.signals: dict[str, SignalResult | None] = {tf: None for tf in settings.timeframes}
        self.history: dict[str, deque] = {tf: deque(maxlen=100) for tf in settings.timeframes}
        self._running = False

    def _verify_results(self, current_price: float):
        """Verifica si señales anteriores alcanzaron TP o SL."""
        for tf in settings.timeframes:
            for sig in self.history[tf]:
                if sig.resultado != TradeResult.PENDIENTE or not sig.trade_setup:
                    continue
                setup = sig.trade_setup
                is_buy = sig.signal in (SignalType.BUY, SignalType.STRONG_BUY)

                if is_buy:
                    if current_price <= setup.sl:
                        sig.resultado = TradeResult.SL_ALCANZADO
                    elif current_price >= setup.tp5:
                        sig.resultado = TradeResult.TP5_ALCANZADO
                    elif current_price >= setup.tp4:
                        sig.resultado = TradeResult.TP4_ALCANZADO
                    elif current_price >= setup.tp3:
                        sig.resultado = TradeResult.TP3_ALCANZADO
                    elif current_price >= setup.tp2:
                        sig.resultado = TradeResult.TP2_ALCANZADO
                    elif current_price >= setup.tp1:
                        sig.resultado = TradeResult.TP1_ALCANZADO
                else:
                    if current_price >= setup.sl:
                        sig.resultado = TradeResult.SL_ALCANZADO
                    elif current_price <= setup.tp5:
                        sig.resultado = TradeResult.TP5_ALCANZADO
                    elif current_price <= setup.tp4:
                        sig.resultado = TradeResult.TP4_ALCANZADO
                    elif current_price <= setup.tp3:
                        sig.resultado = TradeResult.TP3_ALCANZADO
                    elif current_price <= setup.tp2:
                        sig.resultado = TradeResult.TP2_ALCANZADO
                    elif current_price <= setup.tp1:
                        sig.resultado = TradeResult.TP1_ALCANZADO

    async def update_all(self):
        for tf in settings.timeframes:
            try:
                df = await binance_client.fetch_ohlcv(tf)
                signal = await generate_signal(df, tf)
                self._verify_results(signal.price)
                self.signals[tf] = signal
                self.history[tf].append(signal)
            except Exception as e:
                print(f"[DataManager] Error {tf}: {e}")

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

    def get_results(self, timeframe: str) -> list[dict]:
        """Retorna historial con resultados verificados."""
        results = []
        for sig in self.history.get(timeframe, []):
            if sig.trade_setup:
                results.append({
                    "timestamp": sig.timestamp.isoformat(),
                    "signal": sig.signal.value,
                    "price": sig.price,
                    "tp1": sig.trade_setup.tp1,
                    "sl": sig.trade_setup.sl,
                    "resultado": sig.resultado.value,
                })
        return results


data_manager = DataManager()
