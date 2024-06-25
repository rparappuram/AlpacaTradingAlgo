import yfinance as yf
import backtrader as bt

from config import *


class SwingStrategy(bt.Strategy):
    def __init__(self, **kwargs):
        self.params.rsi_period = kwargs.get("rsi_period", RSI_PERIOD)
        self.params.rsi_upper = kwargs.get("rsi_upper", RSI_UPPER)
        self.params.rsi_lower = kwargs.get("rsi_lower", RSI_LOWER)
        self.params.trail_perc = kwargs.get("trail_perc", TRAIL_PERC)
        self.params.atr_period = kwargs.get("atr_period", ATR_PERIOD)
        self.params.atr_loose_multiplier = kwargs.get(
            "atr_loose_multiplier", ATR_LOOSE_MULTIPLIER
        )
        self.params.atr_strict_multiplier = kwargs.get(
            "atr_strict_multiplier", ATR_STRICT_MULTIPLIER
        )
        self.params.backtesting = kwargs.get("backtesting", False)

        self.rsi = {
            data: bt.indicators.RSI(data, period=self.params.rsi_period)
            for data in self.datas
        }
        if self.params.atr_period != 0:
            self.atr = {
                data: bt.indicators.ATR(data, period=self.params.atr_period)
                for data in self.datas
            }
        self.order_reasons = {}
        self.orders = {data: [] for data in self.datas}
        self.trail_orders = {data: [] for data in self.datas}

    def log(self, txt):
        if not self.params.backtesting:
            print(f"{self.datas[0].datetime.date(0)} - {txt}")

    def notify_order(self, order):
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    f"BOUGHT {order.data._name}, Price: ${order.executed.price:.2f}, Size: {order.executed.size}"
                )
            elif order.issell():
                reason = self.order_reasons.get(order.ref, "Unknown Reason")
                self.log(
                    f"SOLD {order.data._name}, Price: ${order.executed.price:.2f}, Size: {order.executed.size} due to {reason}"
                )
                if order.ref in self.order_reasons:  # Clean up after using the reason
                    del self.order_reasons[order.ref]

    def next(self):
        # Step 1: Sell if RSI > self.params.rsi_upper
        positions = self.getpositions()
        for data, pos in positions.items():
            if self.orders[data]:
                new_orders = []
                for order in self.orders[data]:
                    if order.status in [
                        bt.Order.Completed,
                        bt.Order.Canceled,
                        bt.Order.Expired,
                    ]:
                        continue
                    new_orders.append(order)
                self.orders[data] = new_orders
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
                if self.rsi[data] > self.params.rsi_upper:  # Positions should be closed
                    self.log(
                        f"Selling {pos.size} shares of {data._name} at {data.close[0]}"
                    )
                    # Cancel all orders for this stock
                    for trail_order in self.trail_orders[data]:
                        self.cancel(trail_order)
                    self.trail_orders[data] = []
                    if self.orders[data]:
                        for order in self.orders[data]:
                            if order.issell():
                                self.cancel(order)
                        self.orders[data] = []

                    if self.params.atr_period != 0:
                        atr = self.atr[data]
                        order = self.sell(
                            data,
                            size=pos.size,
                            exectype=bt.Order.StopTrail,
                            trailpercent=atr[0] * self.params.atr_strict_multiplier,
                        )
                        order_reason = f"RSI Signal with ATR={atr[0]:.4f} Multiplier={self.params.atr_strict_multiplier} Trail Percent={atr[0] * self.params.atr_strict_multiplier:.4f}"
                    else:
                        order = self.close(data)
                        order_reason = "RSI Signal"

                    self.orders[data].append(order)
                    self.order_reasons[order.ref] = order_reason

        # Step 2: Buy if RSI < self.params.rsi_lower
        # Check stocks to buy
        eligible_stocks = [
            data for data in self.datas if self.rsi[data] < self.params.rsi_lower
        ]

        # Dynamically adjust the budget per stock
        cash = self.broker.get_cash() * 0.9  # Keep 10% as reserve
        num_affordable_stocks = len(eligible_stocks)
        affordable_stocks = []
        for data in eligible_stocks:
            budget_per_stock = cash / num_affordable_stocks
            if data.close[0] <= budget_per_stock:  # affordable
                affordable_stocks.append(data)
            else:  # not affordable
                num_affordable_stocks -= 1
        if not affordable_stocks:
            return  # No buying opportunity

        # Execute buy orders for affordable stocks
        budget_per_stock = cash / len(affordable_stocks)
        for data in affordable_stocks:
            size = int(budget_per_stock / data.close[0])
            if size > 0:
                # self.log(f"Buying {size} shares of {data._name} at {data.close[0]}")

                if self.params.atr_period != 0:
                    atr = self.atr[data]
                    order = self.buy(
                        data,
                        size=size,
                        exectype=bt.Order.StopTrail,
                        trailpercent=atr[0] * self.params.atr_strict_multiplier,
                    )
                else:
                    order = self.buy(data, size=size)

                self.orders[data].append(order)

                trailpercent = (
                    self.atr[data][0] * self.params.atr_loose_multiplier
                    if self.params.atr_period != 0
                    else self.params.trail_perc
                )
                trail_order = self.sell(
                    data,
                    size=size,
                    exectype=bt.Order.StopTrail,
                    trailpercent=trailpercent,
                )
                self.trail_orders[data].append(trail_order)
                self.order_reasons[
                    trail_order.ref
                ] = f"Trailing Stop {trailpercent:.4f}%"

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
        progress=False,
    )
    # add data to cerebro
    for ticker in TICKERS:
        df = data.loc[:, (slice(None), ticker)].copy()
        df.columns = df.columns.droplevel(1)
        feed = bt.feeds.PandasData(dataname=df)
        cerebro.adddata(feed, name=ticker)
    cerebro.broker.set_cash(CASH)
    cerebro.addstrategy(SwingStrategy)
    cerebro.run()
    cerebro.plot()


if __name__ == "__main__":
    run()
