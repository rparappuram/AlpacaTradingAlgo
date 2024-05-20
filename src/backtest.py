import os
import csv
import backtrader as bt
import pandas as pd
import yfinance as yf


# Define the swing trading strategy
class SwingStrategy(bt.Strategy):

    def __init__(
        self,
        rsi_period=14,
        rsi_upper=70,
        rsi_lower=30,
        trail_perc=0.05,
        reverse=True,
        backtesting=False,
    ):
        self.params.rsi_period = rsi_period
        self.params.rsi_upper = rsi_upper
        self.params.rsi_lower = rsi_lower
        self.params.trail_perc = trail_perc
        self.params.reverse = reverse
        self.params.backtesting = backtesting
        self.rsi = {
            data: bt.indicators.RSI(data, period=self.params.rsi_period)
            for data in self.datas
        }
        self.order_reasons = {}
        self.orders = {data: None for data in self.datas}
        self.trail_orders = {data: [] for data in self.datas}

    def log(self, txt):
        if not self.params.backtesting:
            print(f"{self.datas[0].datetime.date(0)} - {txt}")

    def notify_order(self, order):
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    f"BUY {order.data._name}, Price: {order.executed.price}, Size: {order.executed.size}"
                )
            elif order.issell():
                reason = self.order_reasons.get(order.ref, "Unknown Reason")
                self.log(
                    f"SELL {order.data._name}, Price: {order.executed.price}, Size: {order.executed.size} due to {reason}"
                )
                if order.ref in self.order_reasons:  # Clean up after using the reason
                    del self.order_reasons[order.ref]

    def next(self):
        # Step 1: Sell if RSI > self.params.rsi_upper
        positions = self.getpositions()
        for data, pos in positions.items():
            if self.orders[data] and self.orders[data].status in [
                bt.Order.Completed,
                bt.Order.Canceled,
                bt.Order.Expired,
            ]:
                self.orders[data] = None
            if self.trail_orders[data]:
                new_trail_orders = []
                for trail_order in self.trail_orders[data]:
                    if trail_order.status in [
                        bt.Order.Completed,
                        bt.Order.Canceled,
                        bt.Order.Expired,
                    ]:
                        continue
                    new_trail_orders.append(trail_order)
                self.trail_orders[data] = new_trail_orders

            if pos.size:  # Position is open
                if self.rsi[data] > self.params.rsi_upper:
                    # Cancel all trailing stop orders
                    for trail_order in self.trail_orders[data]:
                        self.cancel(trail_order)
                    self.trail_orders[data] = []

                    self.orders[data] = self.close(data)
                    self.order_reasons[self.orders[data].ref] = "RSI Signal"

        # Step 2: Buy if RSI < self.params.rsi_lower
        eligible_stocks = [
            data for data in self.datas if self.rsi[data] < self.params.rsi_lower
        ]
        if not eligible_stocks:
            return  # No buying opportunity

        # Sort eligible stocks by descending order of price
        eligible_stocks.sort(
            key=lambda data: data.close[0], reverse=self.params.reverse
        )

        cash = self.broker.get_cash()
        num_affordable_stocks = len(eligible_stocks)
        affordable_stocks = []

        # Dynamically adjust the budget per stock
        for data in eligible_stocks:
            budget_per_stock = cash / num_affordable_stocks
            if data.close[0] <= budget_per_stock:  # affordable
                affordable_stocks.append(data)
            else:  # not affordable
                num_affordable_stocks -= 1

        # Execute buy orders for affordable stocks
        for data in affordable_stocks:
            budget_per_stock = cash / len(affordable_stocks)
            size = int(budget_per_stock / data.close[0])
            if size > 0:
                self.orders[data] = self.buy(data, size=size)
                trail_order = self.sell(
                    data,
                    size=size,
                    exectype=bt.Order.StopTrail,
                    trailpercent=self.params.trail_perc,
                )
                self.trail_orders[data].append(trail_order)
                self.order_reasons[trail_order.ref] = "Trailing Stop"

    def stop(self):
        print(
            f"{self.datas[0].datetime.date(0)} - Final Portfolio Value: ${self.broker.getvalue():.2f}"
        )
        open_positions = [data for data in self.datas if self.getposition(data).size]
        if open_positions:
            self.log(
                f'Open positions: {", ".join([data._name for data in open_positions])}'
            )
        else:
            self.log("No open positions")


class BacktestFineTuner:
    def __init__(self):
        self.tickers = [
            [
                "AMZN",
                "GOOGL",
                "BAC",
                "DELL",
                "GOOG",
                "TSM",
                "LLY",
                "XOM",
                "PANW",
                "WFC",
                "MRK",
                "PG",
                "TXN",
                "BKNG",
                "C",
                "PYPL",
                "RTX",
                "CMG",
                "FCX",
                "MS",
                "ETN",
                "GM",
                "AXP",
                "SPOT",
            ],
            [
                "ADI",
                "KLAC",
                "PGR",
                "MMM",
                "SCHW",
                "DAL",
                "ELV",
                "WDC",
                "MCHP",
                "BSX",
                "AZN",
                "SWAV",
                "APH",
                "RCL",
                "DVN",
                "CL",
                "TFC",
                "COF",
                "SO",
                "DPZ",
                "KKR",
                "LEN",
                "AEP",
                "JCI",
                "KMB",
                "PH",
                "SHEL",
                "FANG",
                "PNC",
                "D",
                "GD",
                "ALL",
                "TSCO",
                "MCO",
            ],
            [
                "STX",
                "ECL",
                "CPRT",
                "FERG",
                "DLR",
                "WMB",
                "DKS",
                "CNQ",
                "CTAS",
                "WELL",
                "KMI",
                "APO",
                "LHX",
                "PWR",
                "HBAN",
                "AEM",
                "MSI",
                "NDAQ",
                "CVE",
                "PEG",
                "TECK",
                "AMP",
                "PHM",
                "KEY",
                "TCOM",
                "BK",
                "K",
                "CSGP",
                "PSTG",
                "CFG",
                "DFS",
                "FITB",
                "DOV",
                "TRGP",
                "ED",
            ],
            [
                "CTVA",
                "AXON",
                "GPC",
                "ACGL",
                "PRU",
                "CMS",
                "VLTO",
                "CHK",
                "SCCO",
                "RF",
                "ETR",
                "MTB",
                "TSN",
                "OMC",
                "GLW",
                "GNRC",
                "CBOE",
                "ARES",
                "DOCU",
                "AER",
                "AVB",
                "ALLY",
                "IBN",
                "FCNCA",
                "ATMU",
                "LPLA",
                "NTRS",
                "EIX",
                "CNM",
            ],
            [
                "PNR",
                "EQR",
                "PPL",
                "BJ",
                "BALL",
                "RJF",
                "CHD",
                "ZION",
                "NBIX",
                "SNX",
                "FTI",
                "CSL",
                "FLEX",
                "RY",
                "AEO",
                "OC",
                "IBKR",
                "CMA",
                "DVA",
                "EQH",
                "EMN",
                "NVT",
                "HAS",
                "CCEP",
                "ALK",
                "MEDP",
                "CASY",
            ],
            [
                "ESS",
                "PFG",
                "TTE",
                "WFRD",
                "AVY",
                "EWBC",
                "TAL",
                "SHAK",
                "SM",
                "WIRE",
                "JWN",
                "MPLX",
                "RRC",
                "ROIV",
                "KBR",
                "BAH",
                "AIT",
                "AN",
                "BZ",
                "HEI",
                "EXP",
            ],
        ]
        self.start_date = [
            "2023-05-01",  # 12 months
            "2023-12-01",  # 6 months
            "2024-02-01",  # 3 months
            "2024-04-01",  # 1 month
        ]
        self.rsi_period = [7, 14, 21, 28]
        self.rsi_upper = [60, 65, 70, 75, 80]
        self.rsi_lower = [20, 25, 30, 35, 40]
        self.trail_perc = [0.01, 0.02, 0.03, 0.04, 0.05, 0.6, 0.07, 0.08, 0.09, 0.1]
        self.reverse = [True, False]
        self.results = pd.DataFrame(
            columns=[
                "tickers",
                "start_date",
                "rsi_period",
                "rsi_upper",
                "rsi_lower",
                "trail_perc",
                "reverse",
                "final_value",
            ]
        )

    def run(
        self, tickers, start_date, rsi_period, rsi_upper, rsi_lower, trail_perc, reverse
    ):
        cerebro = bt.Cerebro()
        data = yf.download(tickers, start=start_date, interval="1h", progress=False)
        for ticker in tickers:
            df = data.loc[:, (slice(None), ticker)].copy()
            df.columns = df.columns.droplevel(1)
            feed = bt.feeds.PandasData(dataname=df)
            cerebro.adddata(feed, name=ticker)
        cerebro.addstrategy(
            SwingStrategy,
            rsi_period=rsi_period,
            rsi_upper=rsi_upper,
            rsi_lower=rsi_lower,
            trail_perc=trail_perc,
            reverse=reverse,
            backtesting=True,
        )
        cerebro.broker.set_cash(CASH)
        cerebro.run()
        return cerebro.broker.getvalue()

    def finetune(self):
        # Define the path for the CSV file
        csv_file_path = "finetune_results.csv"
        # Check if the file exists to decide whether to write headers
        file_exists = os.path.isfile(csv_file_path)

        with open(csv_file_path, mode="a", newline="") as file:
            fieldnames = [
                "tickers",
                "start_date",
                "rsi_period",
                "rsi_upper",
                "rsi_lower",
                "trail_perc",
                "reverse",
                "final_value",
            ]
            writer = csv.DictWriter(file, fieldnames=fieldnames)

            # Write the header only if the file did not exist
            if not file_exists:
                writer.writeheader()

            for tickers in self.tickers:
                for start_date in self.start_date:
                    for rsi_period in self.rsi_period:
                        for rsi_upper in self.rsi_upper:
                            for rsi_lower in self.rsi_lower:
                                for trail_perc in self.trail_perc:
                                    for reverse in self.reverse:
                                        print(
                                            f"Tickers: {tickers}\nStart Date: {start_date}\nRSI Period: {rsi_period}\nRSI Upper: {rsi_upper}\nRSI Lower: {rsi_lower}\nTrail Perc: {trail_perc}\nReverse: {reverse}"
                                        )
                                        try:
                                            final_value = self.run(
                                                tickers,
                                                start_date,
                                                rsi_period,
                                                rsi_upper,
                                                rsi_lower,
                                                trail_perc,
                                                reverse,
                                            )
                                        except Exception as e:
                                            print(f"Error: {e}")
                                            continue
                                        if final_value > CASH * 20 or final_value < 0:
                                            exit(1)
                                        # Write results to the CSV file for each iteration
                                        writer.writerow(
                                            {
                                                "tickers": tickers,
                                                "start_date": start_date,
                                                "rsi_period": rsi_period,
                                                "rsi_upper": rsi_upper,
                                                "rsi_lower": rsi_lower,
                                                "trail_perc": trail_perc,
                                                "reverse": reverse,
                                                "final_value": final_value,
                                            }
                                        )

    def get_best_params(self):
        self.results = pd.read_csv("finetune_results.csv")
        best_params = self.results.loc[self.results["final_value"].idxmax()]
        return best_params

    def run_best_strategy(self):
        best_params = self.get_best_params()
        tickers = best_params["tickers"]
        start_date = best_params["start_date"]
        rsi_period = best_params["rsi_period"]
        rsi_upper = best_params["rsi_upper"]
        rsi_lower = best_params["rsi_lower"]
        trail_perc = best_params["trail_perc"]
        reverse = best_params["reverse"]
        final_value = self.run(
            tickers, start_date, rsi_period, rsi_upper, rsi_lower, trail_perc, reverse
        )
        return final_value


CASH = 1000
backtest_finetuner = BacktestFineTuner()
backtest_finetuner.finetune()
best_params = backtest_finetuner.get_best_params()
best_params
