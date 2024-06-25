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
                file.flush()

            # remove any rows with nan final_value
            df = pd.read_csv(csv_file_path)
            df = df.dropna(subset=["final_value"])
            df.to_csv(csv_file_path, index=False)

            data = yf.download(
                TICKERS,
                start=START_DATE,
                interval="1d",
                progress=False,
            )

            for combination in itertools.product(*list_attrs.values()):
                # skip if combination is already in csv and has final_value != nan
                # check if combination is already in csv
                skip = False
                with open(csv_file_path, mode="r") as file:
                    reader = csv.DictReader(file)
                    for row in reader:
                        if (
                            all(
                                str(row[key]) == str(value)
                                for key, value in zip(fieldnames[:-1], combination)
                            )
                            and row["final_value"] != "nan"
                        ):
                            skip = True
                            break
                if skip:
                    continue

                # print parameters for this run
                for key, value in zip(fieldnames, combination):
                    print(f"{key} = {value}")

                cerebro = bt.Cerebro()

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
                cerebro.run()

                d = {key: value for key, value in zip(fieldnames, combination)}
                d["final_value"] = cerebro.broker.getvalue()
                writer.writerow(d)

                print("-" * 40)

    def analyze_parameters(self):
        df = pd.read_csv(f"finetune_results_{START_DATE}.csv")
        # if nan in final_value, return
        if df["final_value"].isnull().values.any():
            print("Some final_value is nan, please run finetune() again")
            return
        parameters_analysis = {}
        # get params from row with top 3 final_value
        top_3 = df.nlargest(3, "final_value")
        print(top_3)

        # get mean final_value for each parameter using top 10% of final_value
        for parameter in df.columns[:-1]:
            top_n = int(len(df) * 0.1) if len(df) > 10 else len(df)
            df = df.nlargest(top_n, "final_value")
            results = df.groupby(parameter)["final_value"].mean()
            results = results.sort_values(ascending=False)
            parameters_analysis[parameter] = results
            print(results)
        return parameters_analysis


backtester = Backtester()
backtester.finetune(
)
backtester.analyze_parameters()
