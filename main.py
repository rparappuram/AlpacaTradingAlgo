import os
from dotenv import load_dotenv
load_dotenv()

from src.trader import StockTrader

API_KEY = os.getenv('API_KEY')
SECRET_KEY = os.getenv('SECRET_KEY')
STOCK_LIST = ['AMZN', 'GOOGL', 
    'GOOG', 'TSM', 'LLY', 'XOM', 'PANW', 'BAC', 'DELL', 'WFC',
    'MRK', 'PG', 'TXN', 'BKNG', 'C', 'PYPL', 'RTX', 'CMG', 'FCX', 'MS', 'ETN',
    'GM', 'AXP', 'SPOT', 'ADI', 'KLAC', 'PGR', 'MMM', 'SCHW', 'DAL', 'ELV', 'PXD',
    'WDC', 'MCHP', 'BSX', 'AZN', 'SWAV', 'APH', 'RCL', 'DVN', 'CL', 'TFC', 'COF',
    'SO', 'DPZ', 'KKR', 'LEN', 'AEP', 'JCI', 'KMB', 'PH', 'SHEL', 'FANG', 'PNC',
    'D', 'GD', 'ALL', 'TSCO', 'MCO', 'STX', 'ECL', 'CPRT', 'FERG', 'DLR', 'WMB',
    'DKS', 'CNQ', 'CTAS', 'WELL', 'KMI', 'APO', 'LHX', 'PWR', 'HBAN', 'AEM', 'MSI',
    'NDAQ', 'CVE', 'PEG', 'TECK', 'AMP', 'PHM', 'KEY', 'TCOM', 'BK', 'K', 'CSGP',
    'PSTG', 'CFG', 'DFS', 'FITB', 'DOV', 'TRGP', 'ED', 'CTVA', 'AXON', 'GPC', 'ACGL',
    'PRU', 'CMS', 'VLTO', 'CHK', 'SCCO', 'RF', 'ETR', 'MTB', 'TSN', 'OMC', 'GLW',
    'GNRC', 'CBOE', 'ARES', 'DOCU', 'AER', 'AVB', 'ALLY', 'IBN', 'FCNCA', 'ATMU',
    'LPLA', 'NTRS', 'EIX', 'CNM', 'PNR', 'EQR', 'PPL', 'BJ', 'BALL', 'RJF', 'CHD',
    'ZION', 'NBIX', 'SNX', 'FTI', 'CSL', 'FLEX', 'RY', 'AEO', 'OC', 'IBKR', 'CMA',
    'DVA', 'EQH', 'EMN', 'NVT', 'HAS', 'CCEP', 'ALK', 'MEDP', 'CASY', 'ESS', 'PFG',
    'TTE', 'WFRD', 'AVY', 'EWBC', 'TAL', 'SHAK', 'SM', 'WIRE', 'JWN', 'MPLX', 'RRC',
    'ROIV', 'KBR', 'BAH', 'AIT', 'AN', 'BZ', 'HEI', 'EXP'
]

def main():
    trader = StockTrader(API_KEY, SECRET_KEY, STOCK_LIST, paper=True)
    trader.check_and_trade()

if __name__ == "__main__":
    main()
