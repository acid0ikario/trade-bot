"""Exchange adapter (stub). Real implementation comes in step 01."""

class Exchange:
    def __init__(self, name: str = "binance"):
        self.name = name

    def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int = 500):
        raise NotImplementedError

    def get_price(self, symbol: str) -> float:
        raise NotImplementedError
