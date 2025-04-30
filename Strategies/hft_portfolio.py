#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Portfolio should hande position sizing and current holdings. Will send orders
directly to "brokerage" with predetermined sizing
"""

import datetime
from math import floor
import queue
import numpy as np
import pandas as pd

from event import FillEvent, OrderEvent
from performance import create_sharpe_ratio, create_drawdowns

class PortfolioHFT(object):
    """
    Handles positions and value of all instruments at the resolution of a "bar"
    (second, minute, 5 min, 30 min, 60 min, EOD)

    positions DataFrame stores time index of positions held.

    holdings DataFrame stores cash and total market holdings value for each
    symbol for a time-index. Also stores the % change in portfolio total across
    bars
    """
    def __init__(self, bars, events, start_date, initial_capital=100000.0):
        """
        Initializes portfolio with bars and event queue. Includes a start
        datetime index and capital (USD)

        Parameters
        ----------
        bars : DataHandler object with current market data
        events : Event Queue object
        start_date : start date (bar) of the portfolio
        initial_capital (float) : default is 100k. starting capital in USD
        """
        self.bars = bars
        self.events = events
        self.symbol_list = self.bars.symbol_list
        self.start_date = start_date
        self.initial_capital = initial_capital

        self.all_positions = self.construct_all_positions()
        self.current_positions = dict( (k,v) for k, v in \
                                      [(s,0) for s in self.symbol_list] )
        self.all_holdings = self.construct_all_holdings()
        self.current_holdings = self.construct_current_holdings()

    def construct_all_positions(self):
        """
        Creates a dictionary for each symbol, sets value to 0 for each, and
        adds a datetime key. Then wraps it in a list. Uses start_date to decide
        when the time index begins

        Returns
        -------
        list containing dictionary of all symbols and value at 0
        """
        d = dict( (k,v) for k, v in [(s, 0) for s in self.symbol_list] )
        d['datetime'] = self.start_date
        return [d]

    def construct_all_holdings(self):
        """
        Constructs the holdings list using start_date to determine beggining of
        time index

        'cash' key represents spare cash in account after a purchase
        'commission' key represents cumulative commission accrued
        'total' key represents the total account equity including cash/any open
        positions
        Short positions treated as negative. Starting cash and total are set to
        initial capital

        Returns
        -------
        list containing dictionary with symbols and values (0) and 4 other entries
        """
        d = dict( (k,v) for k, v in [(s, 0) for s in self.symbol_list] )
        d['datetime'] = self.start_date
        d['cash'] = self.initial_capital
        d['commission'] = 0.0
        d['total'] = self.initial_capital
        return [d]

    def construct_current_holdings(self):
        """
        Constructs dictionary to hold instantaneous value of the portfolio
        across all symbols.

        Returns
        -------
        Dictionary of portfolio value across symbol
        """
        d = dict( (k,v) for k, v in [(s, 0.0) for s in self.symbol_list])
        d['cash'] = self.initial_capital
        d['commission'] = 0.0
        d['total'] = self.initial_capital
        return d

#Note, goal here is to update current value of all positions held every time new
#market data is requested from DataHandler object. In live trading this info
#can just be downloaded and parsed from the brokerage. For backtesting it must
#be done manually
#"current market value" will usually be an estimate, we can use last bar received
#for an intraday strategy, but this won't work for a daily strat.


    def update_timeindex(self, event):  #event is unused?
        """
        Adds new record to positions matrix for current market data bar. Reflects
        PREVIOUS bar, all curent market data at this stage is known (OHLCV)

        Parameters
        ----------
        event : ...
        """
        latest_datetime = self.bars.get_latest_bar_datetime(self.symbol_list[0])

        #Update positions
        dp = dict( (k,v) for k,v in [(s,0) for s in self.symbol_list] )
        dp['datetime'] = latest_datetime

        for s in self.symbol_list:
            dp[s] = self.current_positions[s]

        #Append current positions
        self.all_positions.append(dp)

        #Update holdings
        dh = dict( (k,v) for k,v in [(s,0) for s in self.symbol_list] )
        dh['datetime'] = latest_datetime
        dh['cash'] = self.current_holdings['cash']
        dh['commission'] = self.current_holdings['commission']
        dh['total'] = self.current_holdings['cash']

        for s in self.symbol_list:
            #Approximation to the real value
            market_value = self.current_positions[s] * \
                self.bars.get_latest_bar_value(s, "close")
            dh[s] = market_value
            dh['total'] += market_value

        #Append current holdings
        self.all_holdings.append(dh)

    def update_positions_from_fill(self,fill):
        """
        Takes Fill object and updates position matrix to reflect new position

        Parameters
        ----------
        fill : Fill object to update positions with
        """
        #Check whether fill is buy or sell
        fill_dir = 0
        if fill.direction == 'BUY':
            fill_dir = 1
        if fill.direction == 'SELL':
            fill_dir = -1

        #Update positions list with new quantities
        self.current_positions[fill.symbol] += fill_dir*fill.quantity

    def update_holdings_from_fill(self, fill):
        """
        Takes Fill object and updates holdings matrix to reflect holdings value

        In simulating cost of a fill this method doesn't use cost associated
        with the FillEvent since in backtesting the fill cost is unknown
        (depth of book/market impact unknown) and must be estimated
        Thus, "current market price" is used (closing price last bar). Holdings
        for a symbol then set to fill cost * transacted quantity.

        Parameters
        ----------
        fill : Fill object to update holdings with.
        """
        #Check whether fill is buy or sell
        fill_dir = 0
        if fill.direction == 'BUY':
            fill_dir = 1
        if fill.direction == 'SELL':
            fill_dir = -1

        #Update holdings list with new quantities
        fill_cost = self.bars.get_latest_bar_value(fill.symbol, "close")
        cost = fill_dir * fill_cost * fill.quantity
        self.current_holdings[fill.symbol] += cost
        self.current_holdings['commission'] += fill.commission
        self.current_holdings['cash'] -= (cost + fill.commission)
        self.current_holdings['total'] -= (cost + fill.commission)


    def update_fill(self, event):
        """
        updates portfolio current position and holdings

        Parameters
        ----------
        event : FillEvent object
        """
        if event.type == 'FILL':
            self.update_positions_from_fill(event)
            self.update_holdings_from_fill(event)

    def generate_naive_order(self, signal):
        """
        Files an Order object using a constant quantity sizing. No risk management
        or position sizing considerations.

        Parameters
        ----------
        signal : Tuple containing Signal information

        Returns
        -------
        an OrderEvent object
        """
        order = None

        symbol = signal.symbol
        direction = signal.signal_type
        strength = signal.strength

        mkt_quantity = 100
        cur_quantity = self.current_positions[symbol]
        order_type = 'MKT'

        if direction == 'LONG' and cur_quantity == 0:
            order = OrderEvent(symbol, order_type, mkt_quantity, 'BUY')
        if direction == 'SHORT' and cur_quantity == 0:
            order = OrderEvent(symbol, order_type, mkt_quantity, 'SELL')

        if direction == 'EXIT' and cur_quantity > 0:
            order = OrderEvent(symbol, order_type, abs(cur_quantity), 'SELL')
        if direction == 'EXIT' and cur_quantity < 0:
             order = OrderEvent(symbol, order_type, abs(cur_quantity), 'BUY')
        return order

    def update_signal(self, event):
        """
        Acts upon a SignalEvent to generate new orders

        Parameters
        ----------
        event : SignalEvent object
        """
        if event.type == 'SIGNAL':
            order_event = self.generate_naive_order(event)
            self.events.put(order_event)

    def create_equity_curve_dataframe(self):
        """
        Creates a pandas DataFrame from the all_holdings list of dictionaries.
        This is a returns stream that can be used for performance calculations,
        Eq curve will be normalized to % based, hence initial size equal to 1
        """
        curve = pd.DataFrame(self.all_holdings)
        curve.set_index('datetime', inplace=True)
        curve['returns'] = curve['total'].pct_change()
        curve['equity_curve'] = (1.0+curve['returns']).cumprod()
        self.equity_curve = curve

    def output_summary_stats(self):
        """
        Creates a list of summary statistics for the portfolio. Drawdown Duration
        is given in number of bars.

        Returns
        -------
        List of Summary Stats

        """
        total_return = self.equity_curve['equity_curve'].iloc[-1]
        returns = self.equity_curve['returns']
        pnl = self.equity_curve['equity_curve']

        sharpe_ratio = create_sharpe_ratio(returns, periods=252*6.5*60)#Change periods for dif. strats
        drawdown, max_dd, dd_duration = create_drawdowns(pnl)
        self.equity_curve['drawdown'] = drawdown

        stats = [("Total Return", "%0.2f%%" % ((total_return - 1.0)*100.0)), \
                 ("Sharpe Ratio", "%0.2f" % sharpe_ratio),
                 ("Max Drawdown", "%0.2f%%" % (max_dd * 100.0)),
                 ("Drawdown Duration", "%d" % dd_duration)]
        self.equity_curve.to_csv('equity.csv')
        return stats
