import os
import datetime
from dotenv import load_dotenv

load_dotenv()

from src.trading_classes import *
from src.slack_app_notification import *
from slack import WebClient
from slack.errors import SlackApiError


def main(n_stocks=30, n_crypto=30):
    """
    Description: Uses your Alpaca API credentials (including whether you're paper trading or live trading) and
    sells overbought assets in portfolio then buys oversold assets in the market per YahooFinance! opportunities.

    Arguments:
        • st_hr_for_message: starting hour for interval for considering when Slack notification will be sent
        • end_hr_for_message: ending hour for interval for considering when Slack notification will be sent
        • n_stocks: number of top losing stocks from YahooFinance! to be considered for trades
        • n_crypto: number of top traded/valued crypto assets from YahooFinance! to be considered for trades
    """

    current_time = datetime.now(pytz.timezone("US/Eastern"))
    print(f"Timestamp: {current_time.strftime('%Y-%m-%d %I:%M %p')}")

    api = TradingClient(
        api_key=os.getenv("API_KEY"),
        secret_key=os.getenv("SECRET_KEY"),
        paper=True,
    )

    ##############################
    ##############################
    ### Run TradingOpps class

    # Instantiate TradingOpportunities class
    trades = TradingOpportunities(n_stocks=n_stocks, n_crypto=n_crypto)

    # Shows all scraped opportunities; defaults to 25 top losing stocks and 25 of the most popular crypto assets
    trades.get_trading_opportunities()

    # The all_tickers attribute is a list of all tickers in the get_trading_opportunities() method. Passing this list through the get_asset_info() method shows just the tickers that meet buying criteria
    trades.get_asset_info()

    ##############################
    ##############################
    ### Run Alpaca class

    # Instantiate Alpaca class
    Alpaca_instance = Alpaca(api=api)

    # Liquidates currently held assets that meet sell criteria and stores sales in a df
    Alpaca_instance.sell_orders()

    # Execute buy_orders using trades.buy_tickers and stores buys in a tickers_bought list
    Alpaca_instance.buy_orders(tickers=trades.buy_tickers)
    Alpaca_instance.tickers_bought

    ##############################
    ##############################
    ### Slack notification

    # Get orders from the past hour
    orders = slack_app_notification()

    # Authenticate to the Slack API via the generated token
    client = WebClient(os.getenv("SLACK_API"))
    try:
        response = client.chat_postMessage(
            channel=os.getenv("CHANNEL_ID"),
            text=orders,
            mrkdwn=True,
        )
        print("Slack notification sent successfully")
    except SlackApiError as e:
        print(f"Error sending Slack notification: {e}")


if __name__ == "__main__":
    main()
