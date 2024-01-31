import os
import configparser
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetOrdersRequest

from datetime import datetime, timedelta

TIMESTAMP_FILE = "last_run_timestamp.txt"

# These are paper trading config details
config = configparser.ConfigParser()
config.read("creds.cfg")

api = TradingClient(
    api_key=os.getenv("API_KEY"), secret_key=os.getenv("SECRET_KEY"), paper=True
)


def slack_app_notification():
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

    # Get the trade history
    trades = get_trade_history(api)

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
    # Check if the timestamp file exists
    if os.path.exists(TIMESTAMP_FILE):
        with open(TIMESTAMP_FILE, 'r') as file:
            timestamp_str = file.read().strip()
            # Parse the timestamp assuming it's in UTC
            return datetime.fromisoformat(timestamp_str)
    else:
        # Default to one hour ago in UTC if the file doesn't exist
        return datetime.utcnow() - timedelta(hours=1)

def save_current_timestamp():
    # Save the current UTC timestamp to the file
    with open(TIMESTAMP_FILE, 'w') as file:
        # Format the current UTC time as an ISO string
        file.write(datetime.utcnow().isoformat())

def get_trade_history(api):
    last_run_timestamp = get_last_run_timestamp()

    # Retrieve trades since the last run, using the UTC timestamp
    trades = api.get_orders(
        filter=GetOrdersRequest(status="closed", after=last_run_timestamp, direction="desc")
    )

    # Update the timestamp file with the current UTC time
    save_current_timestamp()

    return trades
