import datetime
from pytz import timezone
from alpaca.trading.requests import (
    OrderRequest,
    TrailingStopOrderRequest,
    GetOrdersRequest,
)
from alpaca.trading.enums import OrderSide, OrderType, TimeInForce, QueryOrderStatus
from util import calculate_rsi, calculate_atr, get_current_price
from config import (
    trade_client,
    STOCKS,
    RSI_LOWER,
    RSI_UPPER,
    ATR_MULTIPLIER,
)


def sell_stocks():
    """
    Sell stocks based on the RSI indicator
    """
    print("SELLING STOCKS" + "-" * 100)

    positions = trade_client.get_all_positions()
    for position in positions:
        symbol = position.symbol
        qty = float(position.qty)
        current_price = get_current_price(symbol)

        # Pre-selling checks:
        # 1. Check if there is a FILLED trailing stop order in the last 24 hours
        # 2. Close the position because it's not profitable
        filter = GetOrdersRequest(
            symbols=[symbol],
            status=QueryOrderStatus.CLOSED,
            side=OrderSide.SELL,
            after=datetime.datetime.now() - datetime.timedelta(days=1),
        )
        existing_orders = trade_client.get_orders(filter=filter)
        filled_trailing_stop_symbols = set()
        for order in existing_orders:
            if order.type == OrderType.TRAILING_STOP and symbol not in filled_trailing_stop_symbols:
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
                filled_trailing_stop_symbols.add(symbol)

        # Main selling logic:
        # 1. Check if RSI is above the upper threshold
        # 2. If so, cancel all open (sell trailing stop) orders and close the position
        rsi = calculate_rsi(symbol)
        if rsi > RSI_UPPER:
            # Cancel all open (sell trailing stop) orders
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
    Place a sell trailing stop loss order for all positions
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
            order = TrailingStopOrderRequest(
                symbol=symbol,
                qty=qty_to_cover,
                side=OrderSide.SELL,
                trail_percent=calculate_atr(symbol) * ATR_MULTIPLIER,
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
    eligible_stocks = [stock for stock in STOCKS if calculate_rsi(stock) < RSI_LOWER]
    print(f"Eligible stocks to buy: {eligible_stocks}")
    if not eligible_stocks:
        return  # No buying opportunity

    # Buy eligible stocks
    available_buying_power *= 0.9  # Keep 10% as reserve
    budget_per_stock = available_buying_power / len(eligible_stocks)
    budget_per_stock = round(budget_per_stock, 2)
    if budget_per_stock >= 1.0:
        for stock in eligible_stocks:
            current_price = get_current_price(stock)
            order = OrderRequest(
                symbol=stock,
                notional=budget_per_stock,
                side=OrderSide.BUY,
                type=OrderType.MARKET,
                time_in_force=TimeInForce.DAY,
            )
            print(f"Buying ${budget_per_stock} of {stock} at ${current_price:.2f}")
            trade_client.submit_order(order_data=order)
    else:
        print(f"Insufficient Budget per stock: ${budget_per_stock:}")
    
