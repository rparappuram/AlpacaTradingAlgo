import os

from alpaca.trading import TradingClient
from alpaca.trading.requests import GetOrdersRequest
from datetime import datetime, timedelta


def slack_app_notification(api: TradingClient):
    """
    Description: creates a formatted string detailing

    Arguments:
        • days_hist: examines how many days back you want the bot to gather trading info for
    """
    # Initialize variables for total sales and purchases
    total_sales = 0
    total_purchases = 0

    # Initialize dictionaries to store asset details
    stock_sales = {}
    stock_purchases = {}

    # Get the trade history
    trades = get_trade_history(api)

    # Parse the trade information
    for trade in trades:
        symbol = trade.symbol
        amount = (
            round(float(trade.qty) * float(trade.filled_avg_price), 2)
            if trade.qty
            else round(float(trade.notional), 2)
        )
        if trade.side == "sell":
            total_sales += amount
            stock_sales[symbol] = stock_sales.get(symbol, 0) + amount
        else:
            total_purchases += amount
            stock_purchases[symbol] = stock_purchases.get(symbol, 0) + amount

    # Format the results
    results = []

    total_sales_str = f"*`Total Sales: ${total_sales:,.2f}`*"
    total_purchases_str = f"*`Total Purchases: ${total_purchases:,.2f}`*"

    if stock_sales:
        stock_sales_sorted = sorted(
            stock_sales.items(), key=lambda x: x[1], reverse=True
        )
        stock_sales_formatted = [
            "  _*Stocks: $" + f"{sum(stock_sales.values()):,.2f}*_"
        ]
        for symbol, amount in stock_sales_sorted:
            stock_sales_formatted.append(f"    {symbol} | Amount: ${amount:,.2f}")
        results.append(total_sales_str)
        results += stock_sales_formatted
        results.append("")

    if stock_purchases:
        stock_purchases_sorted = sorted(
            stock_purchases.items(), key=lambda x: x[1], reverse=True
        )
        stock_purchases_formatted = [
            "  _*Stocks: $" + f"{sum(stock_purchases.values()):,.2f}*_"
        ]
        for symbol, amount in stock_purchases_sorted:
            stock_purchases_formatted.append(f"    {symbol} | Amount: ${amount:,.2f}")
        results.append(total_purchases_str)
        results += stock_purchases_formatted

    # Add the available cash and portfolio value
    results.append("")
    results.append(f"*`Day Trade Count: {api.get_account().daytrade_count}`*")
    results.append(f"*`Available Cash: ${api.get_account().cash}`*")
    results.append(f"*`Portfolio Value: ${api.get_account().portfolio_value}`*")

    # Combine the results into a formatted string
    formatted_results = "\n".join(results)

    # Return the formatted results
    return formatted_results


def get_last_run_timestamp():
    # Access the environment variable set by the GitHub Actions workflow
    last_run_timestamp_str = os.getenv("LAST_RUN_TIMESTAMP")

    if last_run_timestamp_str:
        # If the timestamp is found, parse it to a datetime object
        return datetime.fromisoformat(last_run_timestamp_str)
    else:
        # Default to one hour ago if the environment variable isn't set
        return datetime.utcnow() - timedelta(hours=1)


def get_trade_history(api):
    last_run_timestamp = get_last_run_timestamp()

    # Retrieve trades since the last run
    trades = api.get_orders(
        filter=GetOrdersRequest(
            status="closed", after=last_run_timestamp, direction="desc"
        )
    )

    return trades
