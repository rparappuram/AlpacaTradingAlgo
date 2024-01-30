import os
import configparser
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetOrdersRequest

from datetime import datetime, timedelta

# These are paper trading config details
config = configparser.ConfigParser()
config.read("creds.cfg")

api = TradingClient(
    api_key=os.getenv("API_KEY"), secret_key=os.getenv("SECRET_KEY"), paper=True
)


def slack_app_notification(days_hist=1):
    """
    Description: creates a formatted string detailing

    Arguments:
        • days_hist: examines how many days back you want the bot to gather trading info for
    """
    # Initialize variables for total sales and purchases
    total_sales = 0
    total_purchases = 0

    # Initialize dictionaries to store asset details
    crypto_sales = {}
    crypto_purchases = {}
    stock_sales = {}
    stock_purchases = {}

    # Get the trade history for the last 24 hours
    trades = api.get_orders(
        filter=GetOrdersRequest(status="closed", after=datetime.now() - timedelta(days=1), direction="desc")
    )

    # Parse the trade information
    for trade in trades:
        symbol = trade.symbol
        amount = round(float(trade.qty) * float(trade.filled_avg_price), 2) if trade.qty else round(float(trade.notional), 2)
        if trade.side == "sell":
            total_sales += amount
            if "USD" in symbol:
                crypto_sales[symbol] = crypto_sales.get(symbol, 0) + amount
            else:
                stock_sales[symbol] = stock_sales.get(symbol, 0) + amount
        else:
            total_purchases += amount
            if "USD" in symbol:
                crypto_purchases[symbol] = crypto_purchases.get(symbol, 0) + amount
            else:
                stock_purchases[symbol] = stock_purchases.get(symbol, 0) + amount

    # Format the results
    results = []

    total_sales_str = f"*`Total Sales: ${total_sales:,.2f}`*"
    total_purchases_str = f"*`Total Purchases: ${total_purchases:,.2f}`*"

    if crypto_sales:
        crypto_sales_sorted = sorted(
            crypto_sales.items(), key=lambda x: x[1], reverse=True
        )
        crypto_sales_formatted = [
            "  _*Crypto: $" + f"{sum(crypto_sales.values()):,.2f}*_"
        ]
        for symbol, amount in crypto_sales_sorted:
            crypto_sales_formatted.append(f"    {symbol} | Amount: ${amount:,.2f}")
        results.append(total_sales_str)
        results += crypto_sales_formatted
        results.append("")

    if stock_sales:
        stock_sales_sorted = sorted(
            stock_sales.items(), key=lambda x: x[1], reverse=True
        )
        stock_sales_formatted = [
            "  _*Stocks: $" + f"{sum(stock_sales.values()):,.2f}*_"
        ]
        for symbol, amount in stock_sales_sorted:
            stock_sales_formatted.append(f"    {symbol} | Amount: ${amount:,.2f}")
        if not crypto_sales:
            results.append(total_sales_str)
        results += stock_sales_formatted
        results.append("")

    if crypto_purchases:
        crypto_purchases_sorted = sorted(
            crypto_purchases.items(), key=lambda x: x[1], reverse=True
        )
        crypto_purchases_formatted = [
            "  _*Crypto: $" + f"{sum(crypto_purchases.values()):,.2f}*_"
        ]
        for symbol, amount in crypto_purchases_sorted:
            crypto_purchases_formatted.append(f"    {symbol} | Amount: ${amount:,.2f}")
        results.append(total_purchases_str)
        results += crypto_purchases_formatted
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
        if not crypto_purchases:
            results.append(total_purchases_str)
        results += stock_purchases_formatted

    # Combine the results into a formatted string
    formatted_results = "\n".join(results)

    # Return the formatted results
    return formatted_results
