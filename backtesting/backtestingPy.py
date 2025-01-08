import pandas as pd
from backtesting import Backtest, Strategy
from backtesting.test import GOOG


class BB_RSI_Strategy(Strategy):
    bollinger_period = 14
    bollinger_std = 0.8
    bollinger_width_threshold = 0.07
    rsi_period = 14
    rsi_upper = 70
    rsi_lower = 30
    atr_period = 14
    atr_multiplier = 1.5
    cash_multiplier = 0.7

    def init(self):
        self.rsi = self.I(
            lambda x: pd.Series(x)
            .rolling(self.rsi_period)
            .apply(lambda s: pd.Series(s).mean(), raw=False),
            self.data.Close,
        )
        self.bb_mid = self.I(
            lambda x: pd.Series(x).rolling(self.bollinger_period).mean(),
            self.data.Close,
        )
        self.bb_std = self.I(
            lambda x: pd.Series(x).rolling(self.bollinger_period).std(), self.data.Close
        )
        self.bb_upper = self.I(
            lambda mid, std: mid + self.bollinger_std * std, self.bb_mid, self.bb_std
        )
        self.bb_lower = self.I(
            lambda mid, std: mid - self.bollinger_std * std, self.bb_mid, self.bb_std
        )
        self.bb_width = self.I(
            lambda upper, lower: (upper - lower) / lower, self.bb_upper, self.bb_lower
        )

    def next(self):
        if self.position:
            if (
                self.data.Close[-2] > self.bb_upper[-2]
                and self.rsi[-2] > self.rsi_upper
                and self.data.Close[-1] < self.data.Low[-2]
                and self.bb_width[-1] > self.bollinger_width_threshold
            ):
                self.position.close()

        else:
            if (
                self.data.Close[-2] < self.bb_lower[-2]
                # and self.rsi[-2] < self.rsi_lower
                and self.data.Close[-1] > self.data.High[-2]
                and self.bb_width[-1] > self.bollinger_width_threshold
            ):
                self.buy()
                self.sell()


bt = Backtest(GOOG, BB_RSI_Strategy, cash=1000, commission=0)
stats = bt.run()
print(stats)
if stats["Return [%]"] > 0:
    bt.plot()
