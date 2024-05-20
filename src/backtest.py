import backtrader as bt
import yfinance as yf

# Define the swing trading strategy
class SwingStrategy(bt.Strategy):
    params = (
        ('rsi_period', 14),
        ('rsi_upper', 70),
        ('rsi_lower', 30),
        ('trail_perc', 0.05),  # 5% trailing stop loss
    )
    
    def __init__(self):
        self.rsi = {data: bt.indicators.RSI(data, period=self.params.rsi_period) for data in self.datas}
        self.order_reasons = {}
        self.orders = {data: None for data in self.datas}
        self.trail_orders = {data: [] for data in self.datas}

    def log(self, txt):
        print(f'{self.datas[0].datetime.date(0)} - {txt}')


    def notify_order(self, order):
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'BUY {order.data._name}, Price: {order.executed.price}, Size: {order.executed.size}')
            elif order.issell():
                reason = self.order_reasons.get(order.ref, "Unknown Reason")
                self.log(f'SELL {order.data._name}, Price: {order.executed.price}, Size: {order.executed.size} due to {reason}')
                if order.ref in self.order_reasons:  # Clean up after using the reason
                    del self.order_reasons[order.ref]

    def next(self):
        # Step 1: Sell if RSI > 70
        positions = self.getpositions()
        for data, pos in positions.items():
            if self.orders[data] and self.orders[data].status in [bt.Order.Completed, bt.Order.Canceled, bt.Order.Expired]:
                self.orders[data] = None
            if self.trail_orders[data]:
                new_trail_orders = []
                for trail_order in self.trail_orders[data]:
                    if trail_order.status in [bt.Order.Completed, bt.Order.Canceled, bt.Order.Expired]:
                        continue
                    new_trail_orders.append(trail_order)
                self.trail_orders[data] = new_trail_orders
                        
            if pos.size: # Position is open
                if self.rsi[data] > self.params.rsi_upper:
                    # Cancel all trailing stop orders
                    for trail_order in self.trail_orders[data]:
                        self.cancel(trail_order)
                    self.trail_orders[data] = []

                    self.orders[data] = self.sell(data, size=pos.size)
                    self.order_reasons[self.orders[data].ref] = 'RSI Signal'


        # Step 2: Buy if RSI < 30
        eligible_stocks = [data for data in self.datas if self.rsi[data] < self.params.rsi_lower]
        if not eligible_stocks:
            return  # No buying opportunity
        
        # Sort eligible stocks by descending order of price
        eligible_stocks.sort(key=lambda data: data.close[0], reverse=True)
        
        cash = self.broker.get_cash()
        num_affordable_stocks = len(eligible_stocks)
        affordable_stocks = []

        # Dynamically adjust the budget per stock
        for data in eligible_stocks:
            budget_per_stock = cash / num_affordable_stocks
            if data.close[0] <= budget_per_stock: # affordable
                affordable_stocks.append(data)
            else: # not affordable
                num_affordable_stocks -= 1

        # Execute buy orders for affordable stocks
        for data in affordable_stocks:
            budget_per_stock = cash / len(affordable_stocks)
            size = int(budget_per_stock / data.close[0])
            if size > 0:
                self.orders[data] = self.buy(data, size=size)
                trail_order = self.sell(data, size=size, exectype=bt.Order.StopTrail, trailpercent=self.params.trail_perc)
                self.order_reasons[trail_order.ref] = 'Trailing Stop'
                self.trail_orders[data].append(trail_order)
                # self.order_reasons[self.trail_orders[data].ref] = 'Trailing Stop'

    
    def stop(self):
        self.log(f"Final Portfolio Value: ${self.broker.getvalue():.2f}")
        open_positions = [data for data in self.datas if self.getposition(data).size]
        if open_positions:
            self.log(f'Open positions: {", ".join([data._name for data in open_positions])}')
        else:
            self.log('No open positions')


# Load data
def get_data(ticker, start, end=None):
    df = yf.download(ticker, start=start, end=end, interval='1h')
    return bt.feeds.PandasData(dataname=df)

# Set up the environment
cerebro = bt.Cerebro()
tickers = ['AMZN', 'GOOGL', 'BAC', 'DELL',
    # 'GOOG', 'TSM', 'LLY', 'XOM', 'PANW',  'WFC',
    # 'MRK', 'PG', 'TXN', 'BKNG', 'C', 'PYPL', 'RTX', 'CMG', 'FCX', 'MS', 'ETN',
    # 'GM', 'AXP', 'SPOT', 'ADI', 'KLAC', 'PGR', 'MMM', 'SCHW', 'DAL', 'ELV', 'PXD',
    # 'WDC', 'MCHP', 'BSX', 'AZN', 'SWAV', 'APH', 'RCL', 'DVN', 'CL', 'TFC', 'COF',
    # 'SO', 'DPZ', 'KKR', 'LEN', 'AEP', 'JCI', 'KMB', 'PH', 'SHEL', 'FANG', 'PNC',
    # 'D', 'GD', 'ALL', 'TSCO', 'MCO', 'STX', 'ECL', 'CPRT', 'FERG', 'DLR', 'WMB',
    # 'DKS', 'CNQ', 'CTAS', 'WELL', 'KMI', 'APO', 'LHX', 'PWR', 'HBAN', 'AEM', 'MSI',
    # 'NDAQ', 'CVE', 'PEG', 'TECK', 'AMP', 'PHM', 'KEY', 'TCOM', 'BK', 'K', 'CSGP',
    # 'PSTG', 'CFG', 'DFS', 'FITB', 'DOV', 'TRGP', 'ED', 'CTVA', 'AXON', 'GPC', 'ACGL',
    # 'PRU', 'CMS', 'VLTO', 'CHK', 'SCCO', 'RF', 'ETR', 'MTB', 'TSN', 'OMC', 'GLW',
    # 'GNRC', 'CBOE', 'ARES', 'DOCU', 'AER', 'AVB', 'ALLY', 'IBN', 'FCNCA', 'ATMU',
    # 'LPLA', 'NTRS', 'EIX', 'CNM', 'PNR', 'EQR', 'PPL', 'BJ', 'BALL', 'RJF', 'CHD',
    # 'ZION', 'NBIX', 'SNX', 'FTI', 'CSL', 'FLEX', 'RY', 'AEO', 'OC', 'IBKR', 'CMA',
    # 'DVA', 'EQH', 'EMN', 'NVT', 'HAS', 'CCEP', 'ALK', 'MEDP', 'CASY', 'ESS', 'PFG',
    # 'TTE', 'WFRD', 'AVY', 'EWBC', 'TAL', 'SHAK', 'SM', 'WIRE', 'JWN', 'MPLX', 'RRC',
    # 'ROIV', 'KBR', 'BAH', 'AIT', 'AN', 'BZ', 'HEI', 'EXP'
]
start_date = '2024-03-01'
# end_date = '2024-05-10'

for ticker in tickers:
    data = get_data(ticker, start=start_date) # end=end_date)
    cerebro.adddata(data, name=ticker)

cerebro.addstrategy(SwingStrategy)
cerebro.broker.set_cash(1000)  # Set initial cash

cerebro.run()
cerebro.plot()
