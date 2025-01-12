import datetime
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

    def log(self, txt):
        if not self.params.backtesting:
            print(f"{self.datas[0].datetime.date(0)} - {txt}")

    def notify_order(self, order):
        if order.status in [order.Completed]:
            # Check if order is a buy, if so place trailing stop
            if order.isbuy():
                trailpercent = (
                    self.atr[order.data][0] * self.params.atr_multiplier / 100
                )
                trail_order = self.sell(
                    order.data,
                    size=order.executed.size,
                    exectype=bt.Order.StopTrail,
                    trailpercent=trailpercent,
                )

            # Create a tabular format for the log
            action = "BOUGHT" if order.isbuy() else "SOLD"
            stock_name = order.data._name
            price = f"${order.executed.price:.2f}"
            size = f"{order.executed.size}"
            reason = order.getordername()

            # Log in tabular format
            self.log(f"{action:<8} {stock_name:<10} {price:<12} {size:<8} {reason}")

    def next(self):
        # Check positions and decide whether to sell
        self.handle_sell_signals()

        # Check for buying opportunities
        self.handle_buy_signals()

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
                # and is_current_close_above_prev_high
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
                self.buy(data, size=size)

    def handle_sell_signals(self):
        """Handle logic for selling positions."""
        positions = self.getpositions()
        for data, pos in positions.items():
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
                    # and is_current_close_below_prev_low
                    # and is_bb_width_above_threshold
                ):
                    # Cancel any other pending orders for this data
                    all_orders = self.broker.orders
                    for order in all_orders:
                        if order.issell() and data == data:
                            self.cancel(order)

                    # Place a market sell order
                    self.close(data)

    def stop(self):
        """Display detailed final results of the strategy."""
        # Initial and final portfolio values
        initial_value = CASH
        final_value = self.broker.getvalue()

        # Calculate total and annualized percentage return
        total_return = (final_value - initial_value) / initial_value * 100
        start_date = datetime.datetime.strptime(START_DATE, "%Y-%m-%d").date()
        end_date = self.datas[0].datetime.date(0)
        trading_days = (end_date - start_date).days
        annualized_return = ((1 + total_return / 100) ** (365 / trading_days) - 1) * 100

        # Calculate positive/negative trades
        positive_trades = negative_trades = 0
        total_orders = self.broker.orders
        for order in total_orders:
            if order.status in [order.Completed]:
                if order.issell():
                    pnl = order.executed.pnl
                    if pnl > 0:
                        positive_trades += 1
                    elif pnl < 0:
                        negative_trades += 1

        # Display open positions
        open_positions = [data for data in self.datas if self.getposition(data).size]
        if open_positions:
            open_positions_list = ", ".join([data._name for data in open_positions])
        else:
            open_positions_list = "No open positions"

        # Log the results
        print("\nFinal Results Summary")
        print("-" * 40)
        print(f"Initial Portfolio Value: ${initial_value:.2f}")
        print(f"Final Portfolio Value:   ${final_value:.2f}")
        print(f"Total Return:            {total_return:.2f}%")
        print(f"Annualized Return:       {annualized_return:.2f}%")
        print(f"Positive Trades:         {positive_trades}")
        print(f"Negative Trades:         {negative_trades}")
        print(
            f"Trading Period:          {start_date} to {end_date} ({trading_days} days)"
        )
        print(f"Open Positions:          {open_positions_list}")
        print("-" * 40)


def run():
    """
    Run strategy with parameters from config.py.
    Plots the results.
    """
    cerebro = bt.Cerebro(
        oldbuysell=True,
    )
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
