import datetime
from alpaca.trading.requests import (
    OrderRequest,
    TrailingStopOrderRequest,
    GetOrdersRequest,
)
from alpaca.trading.enums import OrderSide, OrderType, TimeInForce
from util import calculate_rsi, get_historical_data
from config import (
    trade_client,
    STOCKS,
    RSI_PERIOD,
    RSI_LOWER_BOUND,
    RSI_UPPER_BOUND,
    TRAIL_PERCENT,
    DATA_RETRIEVAL_PERIOD,
)


def sell_stocks():
    """
    Sell stocks based on the RSI indicator
    """
    print("SELLING STOCKS" + "-" * 100)
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
    print("TRAILING STOP ORDERS" + "-" * 100)
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

        # Place a new trailing stop order for the remaining quantities
        qty_to_cover = int(qty - trailing_stop_order_qty)
        if qty_to_cover > 0:
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
    print("BUYING STOCKS" + "-" * 100)
    account = trade_client.get_account()
    available_cash = float(account.cash)
    print(f"Available cash: ${available_cash:.2f}")
    if available_cash <= 0:
        return

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
    print(f"Eligible stocks to buy: {eligible_stocks}")
    if not eligible_stocks:
        return

    # Buy eligible stocks
    budget_per_stock = available_cash / len(eligible_stocks)
    truncate = lambda x: int(x * 10**9) / 10**9
    budget_per_stock = truncate(budget_per_stock)
    if budget_per_stock <= 0:
        print(f"Insufficient Budget per stock: ${budget_per_stock:.2f}")
        return
    for stock in eligible_stocks:
        # Get current price
        bars = get_historical_data(
            stock,
            datetime.datetime.now() - datetime.timedelta(days=DATA_RETRIEVAL_PERIOD),
        )
        current_price = bars.df["close"].iloc[-1]

        # Place order
        order = OrderRequest(
            symbol=stock,
            notional=budget_per_stock,
            side=OrderSide.BUY,
            type=OrderType.MARKET,
            time_in_force=TimeInForce.DAY,
        )
        print(f"Buying ${budget_per_stock:.2f} of {stock} at ${current_price:.2f}")
        trade_client.submit_order(order_data=order)
