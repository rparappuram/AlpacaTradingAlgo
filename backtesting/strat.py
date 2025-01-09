import yfinance as yf
import backtrader as bt

from parameters import *


class SwingStrategy(bt.Strategy):
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
        self.params.atr_multiplier = kwargs.get("atr_multiplier", ATR_MULTIPLIER)
        self.params.backtesting = kwargs.get("backtesting", False)

        # Initialize indicators
        self.rsi = {
            data: bt.indicators.RSI(data, period=self.params.rsi_period)
            for data in self.datas
        }
        self.atr = {
            data: bt.indicators.ATR(data, period=self.params.atr_period, plot=False)
            for data in self.datas
        }
        self.bollinger = {
            data: bt.indicators.BollingerBands(
                data,
                period=self.params.bollinger_period,
                devfactor=self.params.bollinger_std,
            )
            for data in self.datas
        }
        self.bollinger_width = {
            data: (self.bollinger[data].lines.top - self.bollinger[data].lines.bot)
            / self.bollinger[data].lines.mid
            for data in self.datas
        }

        # Initialize order tracking
        self.order_reasons = {}
        self.orders = {data: [] for data in self.datas}
        self.trail_orders = {data: [] for data in self.datas}

    def log(self, txt):
        if not self.params.backtesting:
            print(f"{self.datas[0].datetime.date(0)} - {txt}")

    def notify_order(self, order):
        if order.status in [order.Completed]:
            reason = self.order_reasons.pop(order.ref, "Unknown Reason")

            # Create a tabular format for the log
            action = "BOUGHT" if order.isbuy() else "SOLD"
            stock_name = order.data._name
            price = f"${order.executed.price:.2f}"
            size = f"{order.executed.size}"

            # Log in tabular format
            self.log(f"{action:<8} {stock_name:<10} {price:<12} {size:<8} {reason}")

    def next(self):
        # Check positions and decide whether to sell
        self.handle_sell_signals()

        # Check for buying opportunities
        self.handle_buy_signals()

    def handle_sell_signals(self):
        """Handle logic for selling positions."""
        positions = self.getpositions()
        for data, pos in positions.items():
            # Remove stale orders
            self.orders[data] = [
                o
                for o in self.orders[data]
                if o.status
                not in [bt.Order.Completed, bt.Order.Canceled, bt.Order.Expired]
            ]
            self.trail_orders[data] = [
                o
                for o in self.trail_orders[data]
                if o.status
                not in [bt.Order.Completed, bt.Order.Canceled, bt.Order.Expired]
            ]

            if pos.size:  # If there's an open position
                # Previous candle conditions
                is_prev_candle_close_above_upper_band = (
                    data.close[-1] > self.bollinger[data].lines.top[-1]
                )
                is_prev_rsi_above_upper_threshold = (
                    self.rsi[data][-1] > self.params.rsi_upper
                )
                # Current candle conditions
                is_current_rsi_above_upper_threshold = (
                    self.rsi[data][0] > self.params.rsi_upper
                )
                is_current_close_below_prev_low = data.close[0] < data.low[-1]
                is_bb_width_above_threshold = (
                    self.bollinger_width[data][0]
                    > self.params.bollinger_width_threshold
                )

                if (
                    is_prev_candle_close_above_upper_band
                    # and is_prev_rsi_above_upper_threshold
                    # and is_current_rsi_above_upper_threshold
                    and is_current_close_below_prev_low
                    # and is_bb_width_above_threshold
                ):
                    # Cancel trailing stop orders
                    for trail_order in self.trail_orders[data]:
                        self.cancel(trail_order)
                    self.trail_orders[data] = []

                    # Cancel any open sell orders
                    if self.orders[data]:
                        for order in self.orders[data]:
                            if order.issell():
                                self.cancel(order)
                        self.orders[data] = []

                    # Place a market sell order
                    order = self.close(data)
                    self.orders[data].append(order)
                    reason = (
                        f"RSI: {self.rsi[data][0]:.2f}"
                        if self.rsi[data] > self.params.rsi_upper
                        else f"Bollinger: {self.bollinger[data].lines.top[0]:.2f}"
                    )
                    self.order_reasons[order.ref] = reason

    def handle_buy_signals(self):
        """Handle logic for buying stocks."""
        # Check for buying opportunities
        eligible_stocks = []
        for data in self.datas:
            # Previous candle conditions
            is_prev_candle_close_below_lower_band = (
                data.close[-1] < self.bollinger[data].lines.bot[-1]
            )
            is_prev_rsi_below_lower_threshold = (
                self.rsi[data][-1] < self.params.rsi_lower
            )
            # Current candle conditions
            is_current_rsi_below_lower_threshold = (
                self.rsi[data][0] < self.params.rsi_lower
            )
            is_current_close_above_prev_high = data.close[0] > data.high[-1]
            is_bb_width_above_threshold = (
                self.bollinger_width[data][0] > self.params.bollinger_width_threshold
            )

            if (
                is_prev_candle_close_below_lower_band
                # and is_prev_rsi_below_lower_threshold
                # and is_current_rsi_below_lower_threshold
                and is_current_close_above_prev_high
                # and is_bb_width_above_threshold
            ):
                eligible_stocks.append(data)

        # Dynamically adjust budget per stock
        cash = self.broker.get_cash() * 0.9  # Reserve 10% of cash
        num_affordable_stocks = len(eligible_stocks)
        affordable_stocks = []
        for data in eligible_stocks:
            budget_per_stock = cash / num_affordable_stocks
            if data.close[0] <= budget_per_stock:  # Stock is affordable
                affordable_stocks.append(data)
            else:  # Stock is not affordable
                num_affordable_stocks -= 1
        if not affordable_stocks:
            return  # No buying opportunities

        # Execute buy orders
        budget_per_stock = cash / len(affordable_stocks)
        for data in affordable_stocks:
            size = int(budget_per_stock / data.close[0])
            if size > 0:
                # Place buy order
                order = self.buy(data, size=size)
                reason = (
                    f"RSI: {self.rsi[data][0]:.2f}"
                    if self.rsi[data] < self.params.rsi_lower
                    else f"Bollinger: {self.bollinger[data].lines.bot[0]:.2f}"
                )
                self.order_reasons[order.ref] = reason
                self.orders[data].append(order)

                # Place sell order with trailing stop
                trailpercent = self.atr[data][0] * self.params.atr_multiplier
                trail_order = self.sell(
                    data,
                    size=size,
                    exectype=bt.Order.StopTrail,
                    trailpercent=trailpercent,
                )
                self.trail_orders[data].append(trail_order)
                self.order_reasons[trail_order.ref] = (
                    f"Trailing Stop {trailpercent:.4f}%"
                )

    def stop(self):
        """Display final results and any open positions."""
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
    # cerebro.addobserver(bt.observers.BuySell)
    data = yf.download(
        TICKERS,
        start=START_DATE,
        interval="1d",
        progress=False,
    )
    data = data.dropna(axis=1)

    # add data to cerebro
    if isinstance(TICKERS, str):
        feed = bt.feeds.PandasData(dataname=data)
        cerebro.adddata(feed, name=TICKERS)
    else:
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
