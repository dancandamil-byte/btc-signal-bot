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

    class Config:
        env_prefix = "BOT_"


settings = Settings()
