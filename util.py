import datetime
from alpaca.data.requests import (
    StockBarsRequest,
)
import pandas as pd
from alpaca.data.timeframe import TimeFrame
from config import data_client, RSI_PERIOD, DATA_RETRIEVAL_PERIOD, ATR_PERIOD


def calculate_atr_percentage(symbol: str) -> float:
    """
    Calculate the Average True Range (ATR) for a given stock
    """
    data = get_historical_data(
        symbol,
        datetime.datetime.now()
        - datetime.timedelta(days=ATR_PERIOD + DATA_RETRIEVAL_PERIOD),
    )
    tr = pd.DataFrame()
    tr["h-l"] = data["high"] - data["low"]
    tr["h-pc"] = abs(data["high"] - data["close"].shift())
    tr["l-pc"] = abs(data["low"] - data["close"].shift())
    tr["tr"] = tr[["h-l", "h-pc", "l-pc"]].max(axis=1)
    atr = tr["tr"].rolling(window=ATR_PERIOD).mean()
    latest_atr = atr.iloc[-1]
    latest_close = data["close"].iloc[-1]
    atr_percentage = (latest_atr / latest_close) * 100
    return atr_percentage


def calculate_rsi(symbol: str) -> float:
    """
    Calculate the Relative Strength Index (RSI) for a given stock
    """
    data = get_historical_data(
        symbol,
        datetime.datetime.now()
        - datetime.timedelta(days=RSI_PERIOD + DATA_RETRIEVAL_PERIOD),
    )
    delta = data["close"].diff()
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


def get_current_price(symbol: str) -> float:
    """
    Get the current price of a stock
    """
    data = get_historical_data(
        symbol,
        datetime.datetime.now() - datetime.timedelta(days=1),
    )
    return data["close"].iloc[-1]
