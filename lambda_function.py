import os
import json
import datetime
from dotenv import load_dotenv

load_dotenv()

from alpaca.trading.requests import (
    OrderRequest,
    TrailingStopOrderRequest,
    GetOrdersRequest,
)
from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, OrderType, TimeInForce
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import (
    StockBarsRequest,
)
from alpaca.data.timeframe import TimeFrame
import datetime
import pandas as pd

# Alpaca API keys
ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
PAPER = True

# Initialize the trading client
trade_client = TradingClient(
    api_key=ALPACA_API_KEY, secret_key=ALPACA_SECRET_KEY, paper=PAPER
)
data_client = StockHistoricalDataClient(
    api_key=ALPACA_API_KEY, secret_key=ALPACA_SECRET_KEY
)

# List of stocks to trade
STOCKS = "AMZN GOOGL BAC DELL GOOG TSM LLY XOM PANW WFC ETN GM AXP SPOT ROIV TAL HBAN KEY KMI RF CVE JWN BZ AEO".split()

# RSI parameters
RSI_PERIOD = 14
DATA_RETRIEVAL_PERIOD = 7
RSI_UPPER_BOUND = 70
RSI_LOWER_BOUND = 30
TRAIL_PERCENT = 6


def lambda_handler(event, context):
    """
    Lambda handler function
    """
    clock = trade_client.get_clock()
    if clock.is_open:
        sell_stocks()
        place_trailing_stop()
        buy_stocks()
        message = "Trading strategy executed successfully"
    else:
        message = "Market is closed"

    return {
        "statusCode": 200,
        "body": json.dumps(message),
    }d


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
    return bars


def sell_stocks():
    """
    Sell stocks based on the RSI indicator
    """
    print("Selling stocks")
    # Check all open positions
    positions = trade_client.get_all_positions()
    for position in positions:
        symbol = position.symbol
        qty = float(position.qty)
        bars = get_historical_data(
            symbol,
            datetime.datetime.now() - datetime.timedelta(days=RSI_PERIOD),
        )
        prices = bars.df["close"]
        current_price = prices.iloc[-1]
        rsi = calculate_rsi(prices)

        if rsi > RSI_UPPER_BOUND:
            # Close the position
            order = OrderRequest(
                symbol=symbol,
                qty=qty,
                side=OrderSide.SELL,
                type=OrderType.MARKET,
                time_in_force=TimeInForce.DAY,
            )
            print(f"Selling {qty} of {symbol} at ${current_price:.2f}")
            trade_client.submit_order(order_data=order)


def place_trailing_stop():
    """
    Place a sell trailing stop order for all open positions
    """
    print("Placing trailing stop orders")
    # Check all open positions
    positions = trade_client.get_all_positions()
    for position in positions:
        symbol = position.symbol
        qty = float(position.qty)
        filter = GetOrdersRequest(symbol=symbol, status="open")
        existing_orders = trade_client.get_orders(filter=filter)

        # Check if there is already a trailing stop order for all quantities
        trailing_stop_order_qty = sum(
            float(order.qty)
            for order in existing_orders
            if order.type == OrderType.TRAILING_STOP
        )
        if trailing_stop_order_qty < qty:
            # Place a new trailing stop order for the remaining quantities
            qty_to_cover = qty - trailing_stop_order_qty
            order = TrailingStopOrderRequest(
                symbol=symbol,
                qty=qty_to_cover,
                side=OrderSide.SELL,
                trail_percent=TRAIL_PERCENT,
                time_in_force=TimeInForce.GTC,
            )
            print(f"Placing trailing stop order for {qty_to_cover} of {symbol}")
            trade_client.submit_order(order_data=order)


def buy_stocks():
    """
    Buy stocks based on the RSI indicator
    """
    print("Buying stocks")
    # Check stocks to buy
    eligible_stocks = []
    for stock in STOCKS:
        bars = get_historical_data(
            stock,
            datetime.datetime.now()
            - datetime.timedelta(days=RSI_PERIOD + DATA_RETRIEVAL_PERIOD),
        )
        prices = bars.df["close"]
        rsi = calculate_rsi(prices)

        # print(f"RSI for {stock}: {rsi}")

        if rsi < RSI_LOWER_BOUND:
            eligible_stocks.append(stock)

    # Buy eligible stocks
    account = trade_client.get_account()
    available_cash = float(account.cash)
    num_eligible_stocks = len(eligible_stocks)
    if num_eligible_stocks == 0:
        print("No stocks to buy")
        return

    for stock in eligible_stocks:
        # Get current price
        bars = get_historical_data(
            stock,
            datetime.datetime.now() - datetime.timedelta(days=DATA_RETRIEVAL_PERIOD),
        )
        current_price = bars.df["close"].iloc[-1]

        # Place order
        budget_per_stock = available_cash / num_eligible_stocks
        order = OrderRequest(
            symbol=stock,
            notional=budget_per_stock,
            side=OrderSide.BUY,
            type=OrderType.MARKET,
            time_in_force=TimeInForce.DAY,
        )
        print(f"Buying ${budget_per_stock:.2f} of {stock} at ${current_price:.2f}")
        # trade_client.submit_order(order_data=order)


if __name__ == "__main__":
    lambda_handler(None, None)
