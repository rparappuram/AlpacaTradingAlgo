import os
from alpaca.trading.client import TradingClient
from alpaca.data.historical import StockHistoricalDataClient


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
STOCKS = "AMZN GOOGL BAC DELL GOOG TSM LLY XOM PANW WFC ETN GM AXP SPOT ROIV HBAN KEY KMI RF CVE JWN BZ AEO FTI IBN PPL FLEX ATMU GLW CFG FITB BAC RRC PNR TAL".split()

# RSI parameters
RSI_PERIOD = 14
DATA_RETRIEVAL_PERIOD = 14
RSI_UPPER_BOUND = 70
RSI_LOWER_BOUND = 25
TRAIL_PERCENT = 6

# Constants
FRACTIONAL_TRADING_DECIMAL_PLACES = 9
