import pandas as pd
import yfinance as yf
from alpaca.trading.requests import OrderRequest
import pytz
import pandas_market_calendars as mcal

from alpaca.trading import TradingClient
from alpaca.common.exceptions import APIError
from ta.volatility import BollingerBands
from ta.momentum import RSIIndicator
from ta.trend import sma_indicator
from tqdm import tqdm
from requests_html import HTMLSession
from datetime import datetime
from colorama import Fore, Style


class TradingOpportunities:
    def __init__(self, n_stocks=25):
        """
        Description:
        Grabs stocks from YahooFinance! to determine trading opportunities using simple technical trading indicators
        such as Bollinger Bands and RSI.

        Arguments:
            •  n_stocks: number of top losing stocks that'll be pulled from YahooFinance! and considered in the algo

        Methods:
            • raw_get_daily_info(): Grabs a provided site and transforms HTML to a pandas df
            • get_trading_opportunities(): Grabs df from raw_get_daily_info() and provides "n" stocks to examine
            • get_asset_info(): a df can be provided to specify which assets you'd like info for since this method is used in the Alpaca class. If no df argument is passed then tickers from get_trading_opportunities() method are used.
        """

        self.n_stocks = n_stocks

    def raw_get_daily_info(self, site):
        """
        Description:
        Grabs a provided site and transforms HTML to a pandas df

        Argument(s):
            • site: YahooFinance! website provided in the get_trading_opportunities() function below

        Other Notes:
        Commented out the conversion of market cap and volume from string to float since this threw an error.
        Can grab this from the yfinance API if needed or come back to this function and fix later.
        """

        session = HTMLSession()
        response = session.get(site)

        tables = pd.read_html(response.html.raw_html)
        df = tables[0].copy()
        df.columns = tables[0].columns

        session.close()
        return df

    def get_trading_opportunities(self):
        """
        Description:
        Grabs df from raw_get_daily_info() and provides self.n_stocks to examine
        """

        df_stock = pd.DataFrame()
        PAGES = ["growth_technology_stocks", "day_losers", "most_actives", "undervalued_growth_stocks"]
        for page in PAGES:
            df = self.raw_get_daily_info(
                f"https://finance.yahoo.com/screener/predefined/{page}?offset=0&count=100"
            )
            df = df.head(self.n_stocks // len(PAGES))
            df_stock = df_stock.append(df)

        # Create a list of all tickers scraped
        self.all_tickers = list(df_stock["Symbol"])

        return df_stock

    def get_asset_info(self, df_current_positions=None):
        """
        Description:
        Grabs historical prices for assets, calculates RSI and Bollinger Bands tech signals, and returns a df with all this data for the assets meeting the buy/sell criteria.

        Argument(s):
            • df_current_positions: a df can be provided to specify which assets you'd like info for since this method is used in the Alpaca class. If no df argument is passed then tickers from get_trading_opportunities() method are used.
        """

        # Grab technical stock info:
        if df_current_positions is None:
            all_tickers = self.all_tickers
        else:
            all_tickers = list(df_current_positions["yf_ticker"])

        df_tech = []
        for i, symbol in tqdm(
            enumerate(all_tickers),
            desc="Grabbing technical metrics for " + str(len(all_tickers)) + " assets",
        ):
            try:
                Ticker = yf.Ticker(symbol)
                Hist = Ticker.history(period="1y", interval="1d")

                for n in [14, 30, 50, 200]:
                    # Initialize MA Indicator
                    Hist["ma" + str(n)] = sma_indicator(
                        close=Hist["Close"], window=n, fillna=False
                    )
                    # Initialize RSI Indicator
                    Hist["rsi" + str(n)] = RSIIndicator(
                        close=Hist["Close"], window=n
                    ).rsi()
                    # Initialize Hi BB Indicator
                    Hist["bbhi" + str(n)] = BollingerBands(
                        close=Hist["Close"], window=n, window_dev=2
                    ).bollinger_hband_indicator()
                    # Initialize Lo BB Indicator
                    Hist["bblo" + str(n)] = BollingerBands(
                        close=Hist["Close"], window=n, window_dev=2
                    ).bollinger_lband_indicator()

                df_tech_temp = Hist.iloc[-1:, -16:].reset_index(drop=True)
                df_tech_temp.insert(0, "Symbol", Ticker.ticker)
                df_tech.append(df_tech_temp)
            except:
                KeyError
            pass

        df_tech = [x for x in df_tech if not x.empty]
        if len(df_tech) > 0:
            df_tech = pd.concat(df_tech)
        else:
            # empty df with columns to avoid errors
            n_nums = [14, 30, 50, 200]
            df_tech = pd.DataFrame(
                columns=["Symbol"]
                + ["ma" + str(n) for n in n_nums]
                + ["rsi" + str(n) for n in n_nums]
                + ["bbhi" + str(n) for n in n_nums]
                + ["bblo" + str(n) for n in n_nums]
            )

        if df_current_positions is None:
            # Define the buy criteria
            buy_criteria = (
                (df_tech[["bblo14", "bblo30", "bblo50", "bblo200"]] == 1).any(axis=1)
            ) | ((df_tech[["rsi14", "rsi30", "rsi50", "rsi200"]] <= 30).any(axis=1))

            # Filter the DataFrame
            filtered_df = df_tech[buy_criteria]
        else:
            # Sales based on technical indicator
            sell_criteria = (
                (df_tech[["bbhi14", "bbhi30", "bbhi50", "bbhi200"]] == 1).any(axis=1)
            ) | ((df_tech[["rsi14", "rsi30", "rsi50", "rsi200"]] >= 70).any(axis=1))

            # Filter the DataFrame
            filtered_df = df_tech[sell_criteria]

        # Create a list of tickers to trade
        self.buy_tickers = list(filtered_df["Symbol"])

        return filtered_df


class Alpaca:
    def __init__(self, api: TradingClient):
        """
        Description: Object providing Alpaca balance details and executes buy/sell trades

        Arguments:
        • api: this object should be created before instantiating the class and it should contain your Alpaca keys
        •

        Methods:
        • get_current_positions(): shows current balance of Alpaca account
        """

        self.api = api

    def get_current_positions(self):
        """
        Description: Returns a df with current positions in account
        """
        positions = self.api.get_all_positions()
        investments = pd.DataFrame(
            {
                "asset": [x.symbol for x in positions],
                "current_price": [x.current_price for x in positions],
                "qty": [x.qty for x in positions],
                "market_value": [x.market_value for x in positions],
                "profit_dol": [x.unrealized_pl for x in positions],
                "profit_pct": [x.unrealized_plpc for x in positions],
            }
        )

        account = self.api.get_account()
        cash = pd.DataFrame(
            {
                "asset": "Cash",
                "current_price": account.cash,
                "qty": account.cash,
                "market_value": account.cash,
                "profit_dol": 0,
                "profit_pct": 0,
            },
            index=[0],
        )  # Need to set index=[0] since passing scalars in df

        assets = pd.concat([investments, cash], ignore_index=True)

        float_fmt = ["current_price", "qty", "market_value", "profit_dol", "profit_pct"]
        str_fmt = ["asset"]

        for col in float_fmt:
            assets[col] = assets[col].astype(float)

        for col in str_fmt:
            assets[col] = assets[col].astype(str)

        rounding_2 = ["market_value", "profit_dol"]
        rounding_4 = ["profit_pct"]

        assets[rounding_2] = assets[rounding_2].apply(lambda x: pd.Series.round(x, 2))
        assets[rounding_4] = assets[rounding_4].apply(lambda x: pd.Series.round(x, 4))

        asset_sum = assets["market_value"].sum()
        assets["portfolio_pct"] = assets["market_value"] / asset_sum

        # Add yf_ticker column so look up of Yahoo Finance! prices is easier
        assets["yf_ticker"] = assets["asset"].apply(
            lambda x: x[:3] + "-" + x[3:] if len(x) == 6 else x
        )

        return assets

    @staticmethod
    def is_market_open():
        nyse = pytz.timezone("US/Eastern")
        current_time = datetime.now(nyse)

        nyse_calendar = mcal.get_calendar("NYSE")
        market_schedule = nyse_calendar.schedule(
            start_date=current_time.date(),
            end_date=current_time.date(),
            start="pre",
            end="post",
        )

        if not market_schedule.empty:
            market_open = (
                market_schedule.iloc[0]["pre"].to_pydatetime().astimezone(nyse)
            )
            market_close = (
                market_schedule.iloc[0]["post"].to_pydatetime().astimezone(nyse)
            )

            if market_open <= current_time <= market_close:
                return True

        return False

    def sell_orders(self):
        """
        Description:
        Liquidates positions of assets currently held based on technical signals or to free up cash for purchases.

        Argument(s):
        • self.df_current_positions: Needed to inform how much of each position should be sold.
        """

        # Get the current positions then filter based on sell criteria
        TradeOpps = TradingOpportunities()
        df_current_positions = self.get_current_positions()
        sell_filtered_df = TradeOpps.get_asset_info(
            df_current_positions=df_current_positions[
                df_current_positions["yf_ticker"] != "Cash"
            ]
        )
        sell_filtered_df["alpaca_symbol"] = sell_filtered_df["Symbol"].str.replace(
            "-", ""
        )
        symbols = list(sell_filtered_df["alpaca_symbol"])
        
        # Submit sell orders
        print(f"{Fore.YELLOW}Selling: {str(symbols)}{Style.RESET_ALL}")
        executed_sales = []
        for symbol in symbols:
            try:
                if symbol in symbols:  # Check if the symbol is in the sell_filtered_df
                    qty = df_current_positions[df_current_positions["asset"] == symbol][
                        "qty"
                    ].values[0]
                    sell_order = self.api.submit_order(
                        order_data=OrderRequest(
                            symbol=symbol,
                            time_in_force="day",
                            qty=qty,
                            side="sell",
                            type="market",
                        )
                    )
                    executed_sales.append([symbol, qty])
            except APIError as e:
                print(f"{Fore.RED}{e}{Style.RESET_ALL}")
                continue

        executed_sales_df = pd.DataFrame(executed_sales, columns=["ticker", "qty"])

        print(f"{Fore.GREEN}Sold:\n{executed_sales_df}{Style.RESET_ALL}")

        # # Check if the Cash row in df_current_positions is at least 10% of total holdings
        # cash_row = df_current_positions[df_current_positions["asset"] == "Cash"]
        # total_holdings = df_current_positions["market_value"].sum()

        # if cash_row["market_value"].values[0] / total_holdings < 0.1:
        #     # Sort the df_current_positions by profit_pct descending
        #     df_current_positions = df_current_positions.sort_values(
        #         by=["profit_pct"], ascending=False
        #     )

        #     # Sell the top 25% of performing assets evenly to make Cash 10% of the total portfolio
        #     top_half = df_current_positions.iloc[: len(df_current_positions) // 4]
        #     top_half_market_value = top_half["market_value"].sum()
        #     cash_needed = total_holdings * 0.1 - cash_row["market_value"].values[0]

        #     for index, row in top_half.iterrows():
        #         print(f"{Fore.YELLOW}Selling {row['asset']} for 10% portfolio cash requirement{Style.RESET_ALL}")
        #         amount_to_sell = int(
        #             (row["market_value"] / top_half_market_value) * cash_needed
        #         )

        #         # If the amount_to_sell is zero or an APIError occurs, continue to the next iteration
        #         if amount_to_sell == 0:
        #             continue

        #         try:
        #             self.api.submit_order(
        #                 order_data=OrderRequest(
        #                     symbol=row["asset"],
        #                     time_in_force="day",
        #                     type="market",
        #                     notional=amount_to_sell,
        #                     side="sell",
        #                 )
        #             )
        #             executed_sales.append([row["asset"], amount_to_sell])
        #         except APIError as e:
        #             print(f"{Fore.RED}{e}{Style.RESET_ALL}")

        #     # Set the locale to the US
        #     locale.setlocale(locale.LC_ALL, "en_US.UTF-8")

        #     # Convert cash_needed to a string with dollar sign and commas
        #     cash_needed_str = locale.currency(cash_needed, grouping=True)

        #     print(f"{Fore.GREEN}Sold {cash_needed_str} of top 25% of performing assets to reach 10% cash position{Style.RESET_ALL}")

        return executed_sales_df

    def buy_orders(self, tickers):
        """
        Description:
        Buys assets per buying opportunities uncovered in the get_asset_info() function.

        Argument(s):
        • df_current_positions: Needed to understand available cash for purchases.
        • symbols: Assets to be purchased.
        """

        # Get the current positions and available cash
        df_current_positions = self.get_current_positions()
        available_cash = df_current_positions[df_current_positions["asset"] == "Cash"][
            "market_value"
        ].values[0]

        # Submit buy orders for eligible symbols
        print(f"{Fore.YELLOW}Buying: {str(tickers)}{Style.RESET_ALL}")
        executed_buys = []
        for symbol in tickers:
            try:
                qty = round(available_cash / len(tickers))
                self.api.submit_order(
                    order_data=OrderRequest(
                        symbol=symbol,
                        type="market",
                        notional=qty,
                        side="buy",
                        time_in_force="day",
                    )
                )
                executed_buys.append([symbol, qty])

            except APIError as e:
                print(f"{Fore.RED}{e}{Style.RESET_ALL}")
                continue

        executed_buys_df = pd.DataFrame(executed_buys, columns=["ticker", "qty"])
        print(f"{Fore.GREEN}Bought:\n{executed_buys_df}{Style.RESET_ALL}")

        self.tickers_bought = tickers
