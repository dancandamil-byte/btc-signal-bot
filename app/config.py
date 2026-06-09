from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    symbol: str = "BTC/USDT"
    timeframes: list[str] = ["1m", "5m", "15m"]
    candle_limit: int = 200
    update_interval: int = 30
    ws_broadcast_interval: int = 5
    blockchain_info_url: str = "https://blockchain.info"
    mempool_url: str = "https://mempool.space/api/v1"
    fear_greed_url: str = "https://api.alternative.me/fng/"
    weight_technical: float = 0.6
    weight_onchain: float = 0.2
    weight_sentiment: float = 0.2
    # Confluencia
    confluence_threshold: float = 0.7
    # Riesgo
    max_atr_multiplier: float = 2.0
    trailing_stop_enabled: bool = True
    # Horarios (UTC)
    session_filter_enabled: bool = True
    sessions: dict[str, list[int]] = {
        "asia": [0, 1, 2, 3, 4, 5, 6, 7],
        "europa": [7, 8, 9, 10, 11, 12, 13, 14, 15],
        "ny": [13, 14, 15, 16, 17, 18, 19, 20, 21],
    }
    low_liquidity_hours: list[int] = [22, 23, 0, 1, 2, 3]
    # DB
    db_path: str = "signals.db"

    class Config:
        env_prefix = "BOT_"


settings = Settings()
