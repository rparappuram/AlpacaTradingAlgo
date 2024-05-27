from alpaca.trading import TradingClient as tradeapi
from alpaca.trading.requests import OrderRequest, TrailingStopOrderRequest
from alpaca.trading.client import TradingClient
from alpaca.trading.stream import TradingStream as streamapi
from alpaca.trading.enums import OrderSide, OrderType, TimeInForce, TradeEvent
from alpaca.data.historical import StockHistoricalDataClient as dataapi
from alpaca.data.requests import (
    StockBarsRequest,
)
from alpaca.data.timeframe import TimeFrame
import datetime
import numpy as np
import pandas as pd


class StockTrader:
    def __init__(
        self,
        api_key: str,
        secret_key: str,
        stock_list: list,
        paper: bool = True,
    ):
        self.trade_api = tradeapi(api_key=api_key, secret_key=secret_key, paper=paper)
        self.data_api = dataapi(api_key=api_key, secret_key=secret_key)
        self.stock_list = stock_list

    def get_historical_data(
        self, symbol: str, start_date: datetime.datetime, end_date: datetime.datetime
    ):
        request_params = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=TimeFrame.Day,
            start=start_date,
            end=end_date,
        )
        bars = self.data_api.get_stock_bars(request_params)
        return bars  # Returns a df

    def buy_stocks(self):
        account = self.trade_api.get_account()
        available_cash = float(account.cash)
        budget_per_stock = available_cash / len(self.stock_list)
        start_date = datetime.datetime.now() - datetime.timedelta(days=100)
        end_date = datetime.datetime.now()
        SUM_SPENT = 0

        for stock in self.stock_list:
            bars = self.get_historical_data(stock, start_date, end_date)
            prices = bars.df["close"]
            short_ma = self.calculate_moving_average(prices, window=20)
            long_ma = self.calculate_moving_average(prices, window=50)

            if (
                short_ma.iloc[-1] > long_ma.iloc[-1]
                and short_ma.iloc[-2] <= long_ma.iloc[-2]
            ):  # Golden cross
                current_price = prices.iloc[-1]
                qty = int(budget_per_stock // current_price)
                if qty > 0:
                    print(
                        f"Placing order for {stock}, qty: {qty}, price: {current_price}"
                    )
                    order_data = OrderRequest(
                        symbol=stock,
                        qty=qty,
                        side=OrderSide.BUY,
                        type=OrderType.MARKET,
                        time_in_force=TimeInForce.DAY,
                    )
                    # self.trade_api.submit_order(order_data=order_data)
                    available_cash -= qty * current_price
                    budget_per_stock = available_cash / (
                        len(self.stock_list) - self.stock_list.index(stock) - 1
                    )
                    SUM_SPENT += qty * current_price

        print(f"Total spent: {SUM_SPENT}")
        print(f"Remaining cash (Local): {available_cash}")
        print(f"Remaining cash (Alpaca): {self.trade_api.get_account().cash}")

    async def update_handler(self, data):
        if data.event == TradeEvent.FILL or data.event == TradeEvent.PARTIAL_FILL:
            order = data.order
            bars = self.get_historical_data(
                order.symbol,
                datetime.datetime.now() - datetime.timedelta(days=30),
                datetime.datetime.now(),
            )
            volatility = np.std(bars.df["close"])
            trail_percent = max(4, volatility)  # Adjust this logic as needed

            print(
                f"Placing sell trailing stop order for {order.symbol}, qty: {data.qty}, trail_percent: {trail_percent}"
            )
            trailing_order_data = TrailingStopOrderRequest(
                symbol=order.symbol,
                qty=data.qty,
                side=OrderSide.SELL,
                time_in_force=TimeInForce.GTC,
                trail_percent=trail_percent,
            )
            # self.trade_api.submit_order(order_data=trailing_order_data)

    def start_trading_stream(self):
        self.trading_stream.run()


def main():
    trader = StockTrader(API_KEY, SECRET_KEY, STOCK_LIST, paper=True)
    trader.buy_stocks()
    # trader.start_trading_stream()


if __name__ == "__main__":
    main()
