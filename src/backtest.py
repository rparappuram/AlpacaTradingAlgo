import itertools
import os
import csv
import traceback
import backtrader as bt
import pandas as pd
import yfinance as yf

from strategy import SwingStrategy


class BacktestFineTuner:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def run(self, **kwargs):
        cerebro = bt.Cerebro()
        tickers = kwargs.pop("tickers")
        data = yf.download(
            tickers,
            start=START_DATE,
            interval="1h",
            progress=False,
        )
        # add data to cerebro
        for ticker in tickers:
            df = data.loc[:, (slice(None), ticker)].copy()
            df.columns = df.columns.droplevel(1)
            feed = bt.feeds.PandasData(dataname=df)
            cerebro.adddata(feed, name=ticker)
        cerebro.broker.set_cash(CASH)
        cerebro.addstrategy(SwingStrategy, **kwargs)
        cerebro.run()
        cerebro.plot()

    def finetune(self):
        csv_file_path = "finetune_results.csv"
        file_exists = os.path.isfile(csv_file_path)

        list_attrs = {k: v for k, v in vars(self).items()}
        fieldnames = list(list_attrs.keys())
        fieldnames.append("final_value")

        with open(csv_file_path, mode="a", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)

            if not file_exists:
                writer.writeheader()

            for combination in itertools.product(*list_attrs.values()):
                # print parameters for this run
                for key, value in zip(fieldnames, combination):
                    print(f"{key} = {value}")

                cerebro = bt.Cerebro()
                tickers = combination[0]
                data = yf.download(
                    tickers,
                    start=START_DATE,
                    interval="1h",
                    progress=False,
                )
                # add data to cerebro
                for ticker in tickers:
                    df = data.loc[:, (slice(None), ticker)].copy()
                    df.columns = df.columns.droplevel(1)
                    feed = bt.feeds.PandasData(dataname=df)
                    cerebro.adddata(feed, name=ticker)
                cerebro.broker.set_cash(CASH)
                params = {
                    key: value for key, value in zip(fieldnames[1:], combination[1:])
                }
                cerebro.addstrategy(SwingStrategy, **params, backtesting=True)
                try:
                    cerebro.run()

                    d = {key: value for key, value in zip(fieldnames, combination)}
                    d["final_value"] = cerebro.broker.getvalue()
                    writer.writerow(d)

                except Exception as e:
                    if ZeroDivisionError:
                        traceback.print_exc()
                    else:
                        raise e


CASH = 1000
START_DATE = "2023-12-01"  # 6 months
backtest_finetuner = BacktestFineTuner(
    tickers=[
        "ROIV TAL HBAN KEY KMI RF CVE JWN BZ AEO".split(),
        "ROIV TAL HBAN KEY KMI RF CVE JWN BZ AEO FTI IBN PPL FLEX ATMU GLW CFG FITB BAC RRC".split(),
        "SM CVE NTRS EWBC WDC CPRT ALK EQH DVA BZ".split(),
        "JWN MPLX SHEL PEG DOV CVE KBR COF TTE GNRC".split(),
        "PNR TAL DOCU DVA KKR PSTG SHEL WELL ALK MPLX".split(),
        "PHM WMB CHD RTX BJ IBN TSM CMA XOM TFC AEP ETR PYPL FITB CCEP AER PEG ZION PNR MTB".split(),
        "APO TSN TRGP RY JCI NVT BAC CNM EWBC BAH PHM PFG TTE ACGL ATMU CCEP BZ STX SNX CFG".split(),
        "AEM STX CBOE IBKR TSM CTVA BJ CPRT AZN NBIX SNX ETR TTE DKS GOOG MPLX PPL SM PSTG DOCU".split(),
        "AMZN GOOGL BAC DELL GOOG TSM LLY XOM PANW WFC".split(),
        "AMZN GOOGL BAC DELL GOOG TSM LLY XOM PANW WFC MRK PG TXN BKNG C PYPL RTX CMG FCX MS".split(),
        "AMZN GOOGL BAC DELL GOOG TSM LLY XOM PANW WFC MRK PG TXN BKNG C PYPL RTX CMG FCX MS ETN GM AXP SPOT".split(),
    ],
    rsi_period=[14, 21, 28],
    rsi_upper=[70, 75, 80],
    rsi_lower=[25, 30, 35],
    trail_perc=[0.03, 0.05, 0.06, 0.08, 0.1],
)
backtest_finetuner.finetune()
