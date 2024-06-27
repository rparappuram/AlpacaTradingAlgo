import datetime
from pytz import timezone
from alpaca.trading.requests import (
    OrderRequest,
    TrailingStopOrderRequest,
    GetOrdersRequest,
)
from alpaca.trading.enums import OrderSide, OrderType, TimeInForce, QueryOrderStatus
from util import get_historical_data, calculate_rsi, calculate_atr
from config import (
    trade_client,
    STOCKS,
    RSI_PERIOD,
    DATA_RETRIEVAL_PERIOD,
    RSI_LOWER,
    RSI_UPPER,
    ATR_PERIOD,
    ATR_MULTIPLIER,
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
        data = get_historical_data(
            symbol,
            datetime.datetime.now()
            - datetime.timedelta(days=RSI_PERIOD + DATA_RETRIEVAL_PERIOD),
        )
        rsi = calculate_rsi(data["close"])
        current_price = data["close"].iloc[-1]

        # Close position if trailing stop order has been filled in last 24 hours
        filter = GetOrdersRequest(
            symbols=[symbol],
            status=QueryOrderStatus.CLOSED,
            side=OrderSide.SELL,
            after=datetime.datetime.now() - datetime.timedelta(days=1),
        )
        existing_orders = trade_client.get_orders(filter=filter)
        for order in existing_orders:
            if order.type == OrderType.TRAILING_STOP:
                time_filled_at = order.filled_at.astimezone(timezone("US/Eastern"))
                print(
                    f"Trailing stop order filled at {time_filled_at} for {order.symbol} {order.qty}"
                )
                order = OrderRequest(
                    symbol=symbol,
                    qty=qty,
                    side=OrderSide.SELL,
                    type=OrderType.MARKET,
                    time_in_force=TimeInForce.DAY,
                )
                print(
                    f"Selling {qty} of {symbol} at ${current_price:.2f} due to FILLED trailing stop order"
                )
                trade_client.submit_order(order_data=order)

        if rsi > RSI_UPPER:
            # Cancel all open orders
            filter = GetOrdersRequest(
                symbols=[symbol], status="open", side=OrderSide.SELL
            )
            existing_orders = trade_client.get_orders(filter=filter)
            for order in existing_orders:
                print(f"Cancelling order: {order.symbol} {order.qty} {order.type}")
                trade_client.cancel_order_by_id(order.id)

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
    positions = trade_client.get_all_positions()
    for position in positions:
        symbol = position.symbol
        qty = float(position.qty)
        filter = GetOrdersRequest(symbols=[symbol], status="open", side=OrderSide.SELL)
        existing_orders = trade_client.get_orders(filter=filter)

        # Check if there is already a trailing stop order for all quantities
        trailing_stop_order_qty = 0.0
        for order in existing_orders:
            if order.type == OrderType.TRAILING_STOP:
                trailing_stop_order_qty += float(order.qty)

        # Place a new trailing stop order for the remaining quantities
        qty_to_cover = int(qty - trailing_stop_order_qty)
        if qty_to_cover > 0:
            data = get_historical_data(
                symbol,
                datetime.datetime.now()
                - datetime.timedelta(days=ATR_PERIOD + DATA_RETRIEVAL_PERIOD),
            )
            atr = calculate_atr(data)
            trailing_stop_percent = atr * ATR_MULTIPLIER
            order = TrailingStopOrderRequest(
                symbol=symbol,
                qty=qty_to_cover,
                side=OrderSide.SELL,
                trail_percent=trailing_stop_percent,
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
    available_buying_power = float(account.buying_power)
    print(f"Available buying power: ${available_buying_power:.2f}")

    # Check stocks to buy
    eligible_stocks = []
    for stock in STOCKS:
        prices = get_historical_data(
            stock,
            datetime.datetime.now()
            - datetime.timedelta(days=RSI_PERIOD + DATA_RETRIEVAL_PERIOD),
        )
        rsi = calculate_rsi(prices["close"])

        # print(f"RSI for {stock}: {rsi}")

        if rsi < RSI_LOWER:
            eligible_stocks.append(stock)
    print(f"Eligible stocks to buy: {eligible_stocks}")
    if not eligible_stocks:
        return  # No buying opportunity

    # Buy eligible stocks
    available_buying_power *= 0.9  # Keep 10% as reserve
    budget_per_stock = available_buying_power / len(eligible_stocks)
    budget_per_stock = round(budget_per_stock, 2)
    if budget_per_stock <= 0:
        print(f"Insufficient Budget per stock: ${budget_per_stock:}")
        return
    for stock in eligible_stocks:
        # Get current price
        prices = get_historical_data(
            stock,
            datetime.datetime.now() - datetime.timedelta(days=DATA_RETRIEVAL_PERIOD),
        )
        current_price = prices["close"].iloc[-1]

        # Place order
        order = OrderRequest(
            symbol=stock,
            notional=budget_per_stock,
            side=OrderSide.BUY,
            type=OrderType.MARKET,
            time_in_force=TimeInForce.DAY,
        )
        print(f"Buying ${budget_per_stock} of {stock} at ${current_price:.2f}")
        trade_client.submit_order(order_data=order)
