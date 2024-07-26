import yfinance as yf
import backtrader as bt

from parameters import *


class BollingerBandsRSI(bt.Strategy):
    def __init__(self, **kwargs):
        self.params.bollinger_period = kwargs.get("bollinger_period", BOLLINGER_PERIOD)
        self.params.bollinger_std = kwargs.get("bollinger_std", BOLLINGER_STD)
        self.params.bollinger_width_threshold = kwargs.get(
            "bollinger_width_threshold", BOLLINGER_WIDTH_THRESHOLD
        )
        self.params.rsi_period = kwargs.get("rsi_period", RSI_PERIOD)
        self.params.rsi_upper = kwargs.get("rsi_upper", RSI_UPPER)
        self.params.rsi_lower = kwargs.get("rsi_lower", RSI_LOWER)
        self.params.atr_period = kwargs.get("atr_period", ATR_PERIOD)
        self.params.atr_multiplier = kwargs.get("atr_multiplier", ATR_MULTIPLER)
        self.params.backtesting = kwargs.get("backtesting", False)
        for data in self.datas:
            self.bb = bt.indicators.BollingerBands(
                data,
                period=self.params.bollinger_period,
                devfactor=self.params.bollinger_std,
            )
            self.bb_width = (self.bb.lines.top - self.bb.lines.bot) / self.bb.lines.mid
            self.rsi = bt.indicators.RSI(data, period=self.params.rsi_period)
            self.atr = bt.indicators.ATR(data, period=self.params.atr_period)

    def log(self, txt):
        if not self.params.backtesting:
            print(f"{self.datas[0].datetime.date(0)} - {txt}")

    def notify_order(self, order):
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    f"BOUGHT {order.data._name}, Price: ${order.executed.price:.2f}, Size: {order.executed.size}"
                )
                trail_percent = (
                    ((self.atr[0] / self.data.close[0]) * 100)
                    * self.params.atr_multiplier
                ) / 100
                self.sell(
                    data=order.data,
                    exectype=bt.Order.StopTrail,
                    trailpercent=trail_percent,
                )
                self.log(
                    f"Trailing stop set for {order.data._name} at {(trail_percent*100):.2f}%"
                )
            elif order.issell():
                self.log(
                    f"SOLD {order.data._name}, Price: ${order.executed.price:.2f}, Size: {order.executed.size}"
                )

    def next(self):
        positions = self.getpositions()
        to_sell = []
        for data, pos in list(positions.items()):
            if pos.size:
                # Previous candle conditions
                is_prev_candle_close_above_upper_band = data.close[-1] > self.bb.top[-1]
                is_prev_rsi_above_threshold = self.rsi[-1] > self.params.rsi_upper
                # Current candle conditions
                is_current_close_below_prev_low = data.close[0] < data.low[-1]
                is_bb_width_greater_than_threshold = (
                    self.bb_width[0] > self.params.bollinger_width_threshold
                )

                if (
                    self.position
                    and is_prev_candle_close_above_upper_band
                    and is_prev_rsi_above_threshold
                    and is_current_close_below_prev_low
                    and is_bb_width_greater_than_threshold
                ):
                    self.sell(data=data)

        # Step 2: check BUY signal
        to_buy = []
        for data in self.datas:
            # Previous candle conditions
            is_prev_candle_close_below_lower_band = data.close[-1] < self.bb.bot[-1]
            is_prev_rsi_below_threshold = self.rsi[-1] < self.params.rsi_lower
            # Current candle conditions
            is_current_close_above_prev_high = data.close[0] > data.high[-1]
            is_bb_width_greater_than_threshold = (
                self.bb_width[0] > self.params.bollinger_width_threshold
            )

            if (
                is_prev_candle_close_below_lower_band
                and is_prev_rsi_below_threshold
                and is_current_close_above_prev_high
                and is_bb_width_greater_than_threshold
            ):
                to_buy.append(data)

        # Dynamically adjust the budget per stock
        cash = self.broker.get_cash()
        budget = cash * 0.9  # keep 10% as reserve
        num_affordable_stocks = len(to_buy)
        affordable_stocks = []
        for data in to_buy:
            budget_per_stock = budget / num_affordable_stocks
            if data.close[0] <= budget_per_stock:
                affordable_stocks.append(data)
            else:
                num_affordable_stocks -= 1
        if not affordable_stocks:
            return

        budget_per_stock = budget / num_affordable_stocks
        for data in affordable_stocks:
            size = int(budget_per_stock / data.close[0])
            if size > 0:
                self.buy(data, size=size)

    def stop(self):
        print(f"Final Portfolio Value: ${self.broker.getvalue():.2f}")
        open_positions = [data for data in self.datas if self.getposition(data).size]
        if open_positions:
            self.log(
                f'Open positions: {", ".join([data._name for data in open_positions])}'
            )
        else:
            self.log("No open positions")


def run():
    """
    Run strategy with parameters from config.py.
    Plots the results.
    """
    cerebro = bt.Cerebro()
    data = yf.download(
        TICKERS,
        start=START_DATE,
        interval="1d",
    )
    data = data.dropna(axis=1)

    # add data to cerebro
    if type(TICKERS) == str:
        ticker = TICKERS
        feed = bt.feeds.PandasData(dataname=data)
        cerebro.adddata(feed, name=ticker)
    else:
        for ticker in TICKERS:
            df = data.loc[:, (slice(None), ticker)].copy()
            df.columns = df.columns.droplevel(1)
            feed = bt.feeds.PandasData(dataname=df)
            cerebro.adddata(feed, name=ticker)

    cerebro.broker.set_cash(CASH)
    cerebro.addstrategy(BollingerBandsRSI)
    cerebro.run()
    cerebro.plot()


if __name__ == "__main__":
    run()
