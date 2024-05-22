import itertools
import os
import csv
import traceback
import backtrader as bt
import pandas as pd
import yfinance as yf

from strategy import SwingStrategy
from config import *


class BacktestFineTuner:
    def __init__(self, **kwargs):
        print("=" * 80)
        print(f"START_DATE = {START_DATE}")
        for key, value in kwargs.items():
            setattr(self, key, value)
            print(f"{key} = {value}")
        print("=" * 80)

    def run(self, **kwargs):
        cerebro = bt.Cerebro()
        data = yf.download(
            TICKERS,
            start=START_DATE,
            interval="1h",
            progress=False,
        )
        # add data to cerebro
        for ticker in TICKERS:
            df = data.loc[:, (slice(None), ticker)].copy()
            df.columns = df.columns.droplevel(1)
            feed = bt.feeds.PandasData(dataname=df)
            cerebro.adddata(feed, name=ticker)
        cerebro.broker.set_cash(CASH)
        cerebro.addstrategy(SwingStrategy, **kwargs)
        cerebro.run()
        cerebro.plot()

    def finetune(self):
        csv_file_path = f"finetune_results_{START_DATE}.csv"
        file_exists = os.path.isfile(csv_file_path)

        list_attrs = {k: v for k, v in vars(self).items()}
        fieldnames = list(list_attrs.keys())
        fieldnames.append("final_value")

        with open(csv_file_path, mode="a", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)

            if not file_exists:
                writer.writeheader()

            for combination in itertools.product(*list_attrs.values()):
                # skip if combination is already in csv and has final_value != nan
                # check if combination is already in csv
                skip = False
                with open(csv_file_path, mode="r") as file:
                    reader = csv.DictReader(file)
                    for row in reader:
                        if all(
                            str(row[key]) == str(value)
                            for key, value in zip(fieldnames[:-1], combination)
                        ):
                            skip = True
                            break
                if skip:
                    continue

                # print parameters for this run
                # for key, value in zip(fieldnames, combination):
                #     print(f"{key} = {value}")

                cerebro = bt.Cerebro()
                data = yf.download(
                    TICKERS,
                    start=START_DATE,
                    interval="1h",
                    progress=False,
                )
                # add data to cerebro
                for ticker in TICKERS:
                    df = data.loc[:, (slice(None), ticker)].copy()
                    df.columns = df.columns.droplevel(1)
                    feed = bt.feeds.PandasData(dataname=df)
                    cerebro.adddata(feed, name=ticker)
                cerebro.broker.set_cash(CASH)
                params = {
                    key: value for key, value in zip(fieldnames[:-1], combination)
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

    def analyze_parameters(self):
        df = pd.read_csv(f"finetune_results_{START_DATE}.csv")
        # if nan in final_value, return
        if df["final_value"].isnull().values.any():
            print("Some final_value is nan, please run finetune() again")
            return
        parameters_analysis = {}
        # get params from row with max final_value
        max_final_value = df["final_value"].max()
        max_final_value_row = df[df["final_value"] == max_final_value]
        print(max_final_value_row)
        for parameter in df.columns[:-1]:
            results = df.groupby(parameter)["final_value"].mean()
            results = results.sort_values(ascending=False)
            parameters_analysis[parameter] = results
            print(results)
        return parameters_analysis


backtest_finetuner = BacktestFineTuner(
    rsi_upper=[70, 75],
    rsi_lower=[25, 30, 35],
    trail_perc=[0.03, 0.05, 0.06, 0.08, 0.1],
)
backtest_finetuner.finetune()
backtest_finetuner.analyze_parameters()
