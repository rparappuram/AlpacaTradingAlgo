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

    def get_best_params(self):
        results = pd.read_csv("finetune_results.csv")
        best_params = results.loc[results["final_value"].idxmax()]
        return best_params


CASH = 1000
START_DATE = "2023-12-01"  # 6 months
backtest_finetuner = BacktestFineTuner(
    tickers=[
        "AMZN GOOGL BAC DELL GOOG TSM LLY XOM PANW WFC MRK PG TXN BKNG C PYPL RTX CMG FCX MS ETN GM AXP SPOT".split(),
        "ADI KLAC PGR MMM SCHW DAL ELV WDC MCHP BSX AZN SWAV APH RCL DVN CL TFC COF SO DPZ KKR LEN AEP JCI KMB PH SHEL FANG PNC D GD ALL TSCO MCO".split(),
        "STX ECL CPRT FERG DLR WMB DKS CNQ CTAS WELL KMI APO LHX PWR HBAN AEM MSI NDAQ CVE PEG TECK AMP PHM KEY TCOM BK K CSGP PSTG CFG DFS FITB DOV TRGP ED".split(),
        "CTVA AXON GPC ACGL PRU CMS VLTO CHK SCCO RF ETR MTB TSN OMC GLW GNRC CBOE ARES DOCU AER AVB ALLY IBN FCNCA ATMU LPLA NTRS EIX CNM".split(),
        "PNR EQR PPL BJ BALL RJF CHD ZION NBIX SNX FTI CSL FLEX RY AEO OC IBKR CMA DVA EQH EMN NVT HAS CCEP ALK MEDP CASY".split(),
        "ESS PFG TTE WFRD AVY EWBC TAL SHAK SM WIRE JWN MPLX RRC ROIV KBR BAH AIT AN BZ HEI EXP".split(),
    ],
    rsi_period=[14, 21, 28],
    rsi_upper=[60, 65, 70, 75, 80],
    rsi_lower=[20, 25, 30, 35, 40],
    trail_perc=[0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.09, 0.1, 0.15, 0.2, 0.25],
    reverse=[True, False, None],
)
backtest_finetuner.finetune()
# best_params = backtest_finetuner.get_best_params()
# print(best_params)
# backtest_finetuner.run_and_plot(**best_params)
