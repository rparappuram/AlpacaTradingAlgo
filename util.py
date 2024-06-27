import datetime
from alpaca.data.requests import (
    StockBarsRequest,
)
import pandas as pd
from alpaca.data.timeframe import TimeFrame
from config import data_client, RSI_PERIOD


def calculate_atr(data: pd.DataFrame, n: int = 7) -> pd.Series:
    """
    Calculate the Average True Range (ATR) for a given stock
    """
    high_low = data["high"] - data["low"]
    high_close = (data["high"] - data["close"].shift()).abs()
    low_close = (data["low"] - data["close"].shift()).abs()

    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)

    atr = true_range.rolling(window=n).mean()
    return atr


def calculate_rsi(prices: pd.Series) -> float:
    """
    Calculate the Relative Strength Index (RSI) for a given stock
    """
    delta = prices.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    avg_gain = gain.rolling(window=RSI_PERIOD).mean()
    avg_loss = loss.rolling(window=RSI_PERIOD).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    return rsi.iloc[-1]


def get_historical_data(
    symbol: str,
    start_date: datetime.datetime,
    end_date: datetime.datetime = datetime.datetime.now()
    - datetime.timedelta(minutes=20),
):
    """
    Get historical data for a given stock
    """
    request_params = StockBarsRequest(
        symbol_or_symbols=symbol,
        timeframe=TimeFrame.Day,
        start=start_date,
        end=end_date,
    )
    bars = data_client.get_stock_bars(request_params)
    return bars.df
