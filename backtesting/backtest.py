import itertools
import os
import csv
import traceback
import backtrader as bt
import pandas as pd
import yfinance as yf

from strategy import SwingStrategy
from config import *


class Backtester:
    def run(self, **kwargs):
        """
        Run strategy with parameters from config.py.
        Plots the results.
        """
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

    def finetune(self, **kwargs):
        print("=" * 80)
        print(f"""BacktestFineTuner with parameters:""")
        for key, value in kwargs.items():
            setattr(self, key, value)
            print(f"{key} = {value}")
        print("=" * 80)

        csv_file_path = f"finetune_results_{START_DATE}.csv"
        file_exists = os.path.isfile(csv_file_path)

        list_attrs = {k: v for k, v in vars(self).items()}
        fieldnames = list(list_attrs.keys())
        fieldnames.append("final_value")

        with open(csv_file_path, mode="a", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)

            if not file_exists:
                writer.writeheader()

            # remove any rows with nan final_value
            df = pd.read_csv(csv_file_path)
            df = df.dropna(subset=["final_value"])
            df.to_csv(csv_file_path, index=False)

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
                        ) and row["final_value"] != "nan":
                            skip = True
                            break
                if skip:
                    continue

                # print parameters for this run
                for key, value in zip(fieldnames, combination):
                    print(f"{key} = {value}")
                print("-" * 40)

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


backtester = Backtester()
backtester.run()
# backtester.finetune(
#     # rsi_period=[14],
#     # rsi_upper=[70],
#     # rsi_lower=[25, 30],
#     # trail_perc=[0.06],
#     atr_period=[14],
#     atr_loose_multiplier=[.5, 1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5] ,
#     atr_strict_multiplier=[0.01, .05, .1, .2, .3, .4, .5, .6, .7, .8, .9, 1],
# )
# backtester.analyze_parameters()