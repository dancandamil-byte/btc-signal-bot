import asyncio
from collections import deque

from app.config import settings
from app.models import SignalResult, SignalType, TradeResult
from app.services.binance_client import binance_client
from app.services.database import save_signal, update_result, get_stats, get_history_db
from app.signals.engine import generate_signal


class DataManager:
    def __init__(self):
        self.signals: dict[str, SignalResult | None] = {tf: None for tf in settings.timeframes}
        self.history: dict[str, deque] = {tf: deque(maxlen=100) for tf in settings.timeframes}
        self.signal_ids: dict[str, deque] = {tf: deque(maxlen=100) for tf in settings.timeframes}
        self._running = False

    def _multi_tf_aligned(self, signal: SignalResult) -> bool:
        """Verifica si la señal está alineada con timeframes superiores."""
        if signal.signal == SignalType.NEUTRAL:
            return True  # No filtrar neutrales

        tf_order = settings.timeframes
        current_idx = tf_order.index(signal.timeframe) if signal.timeframe in tf_order else 0

        # Verificar TFs superiores
        for tf in tf_order[current_idx + 1:]:
            higher_signal = self.signals.get(tf)
            if higher_signal and higher_signal.signal != SignalType.NEUTRAL:
                is_buy = signal.signal in (SignalType.BUY, SignalType.STRONG_BUY)
                higher_is_buy = higher_signal.signal in (SignalType.BUY, SignalType.STRONG_BUY)
                if is_buy != higher_is_buy:
                    return False  # Conflicto con TF superior
        return True

    def _apply_trailing_stop(self, sig: SignalResult, current_price: float, sig_idx: int, tf: str):
        """Aplica trailing stop: mueve SL cuando alcanza TP."""
        if not sig.trade_setup or not settings.trailing_stop_enabled:
            return
        if sig.resultado != TradeResult.PENDIENTE:
            return

        setup = sig.trade_setup
        is_buy = sig.signal in (SignalType.BUY, SignalType.STRONG_BUY)

        if is_buy:
            if current_price >= setup.tp3:
                sig.trailing_sl = setup.tp2
            elif current_price >= setup.tp2:
                sig.trailing_sl = setup.tp1
            elif current_price >= setup.tp1:
                sig.trailing_sl = setup.entry_min

            # Verificar SL o trailing
            effective_sl = sig.trailing_sl or setup.sl
            if current_price <= effective_sl:
                if sig.trailing_sl:
                    sig.resultado = TradeResult.TRAILING_STOP
                else:
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
            if current_price <= setup.tp3:
                sig.trailing_sl = setup.tp2
            elif current_price <= setup.tp2:
                sig.trailing_sl = setup.tp1
            elif current_price <= setup.tp1:
                sig.trailing_sl = setup.entry_max

            effective_sl = sig.trailing_sl or setup.sl
            if current_price >= effective_sl:
                if sig.trailing_sl:
                    sig.resultado = TradeResult.TRAILING_STOP
                else:
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

        # Actualizar DB si resultado cambió
        if sig.resultado != TradeResult.PENDIENTE:
            ids = list(self.signal_ids[tf])
            if sig_idx < len(ids):
                update_result(ids[sig_idx], sig.resultado.value, sig.trailing_sl)

    def _verify_results(self, current_price: float):
        for tf in settings.timeframes:
            for idx, sig in enumerate(self.history[tf]):
                self._apply_trailing_stop(sig, current_price, idx, tf)

    async def update_all(self):
        for tf in settings.timeframes:
            try:
                df = await binance_client.fetch_ohlcv(tf)
                signal = await generate_signal(df, tf)

                # Multi-TF check
                if not self._multi_tf_aligned(signal) and signal.signal != SignalType.NEUTRAL:
                    signal.filtered_reason = "Conflicto multi-timeframe"
                    signal.mensaje = f"⚠️ Filtrada: TF superiores en conflicto\n📍 ${signal.price:,.0f} | {tf}"
                    signal.signal = SignalType.NEUTRAL
                    signal.trade_setup = None

                self._verify_results(signal.price)
                self.signals[tf] = signal
                self.history[tf].append(signal)

                # Guardar en SQLite
                sig_id = save_signal(signal)
                self.signal_ids[tf].append(sig_id)
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

    def get_stats(self, timeframe: str | None = None):
        return get_stats(timeframe)

    def get_results_db(self, timeframe: str) -> list[dict]:
        return get_history_db(timeframe)


data_manager = DataManager()
