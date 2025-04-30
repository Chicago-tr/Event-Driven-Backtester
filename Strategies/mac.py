#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import print_function

import datetime

import numpy as np
import pandas as pd
import statsmodels.api as sm

from strategy import Strategy
from event import SignalEvent
from backtest import Backtest
from data import HistoricCSVDataHandler
from execution import SimulatedExecutionHandler
from portfolio import Portfolio


class MovingAverageCrossStrategy(Strategy):
    """
    Carries out a Moving Average Crossover strategy with a long/short simple
    weighted moving average. Default long/short windows are 400/100 respectively.
    """

    def __init__(self, bars, events, short_window=5, long_window=20):
        """
        Initializes MA Cross strategy.

        Parameters
        ----------
        bars : DataHandler object that provides bar info
        events : Event Queue object
        short_window : Short moving avg.lookback, optional, The default is 100.
        long_window : Long moving avg.lookback, optional, The default is 400.
        """
        self.bars = bars
        self.symbol_list = self.bars.symbol_list
        self.events = events
        self.short_window = short_window
        self.long_window = long_window

        #Set to True if symbol is in the market
        self.bought = self._calculate_initial_bought()

    def _calculate_initial_bought(self):
        """
        Adds keys (symbols) to the bought dictionary and sets values to 'OUT'.

        Returns
        -------
        Dictionary with keys of each symbol in symbol_list and values to 'OUT'.
        """
        bought = {}
        for s in self.symbol_list:
            bought[s] = 'OUT'
        return bought


    def calculate_signals(self, event):
        """
        Generate signals based on MAC SMA. Short window crossing the long
        window -> Long entry and vice versa for short.

        Parameters
        ----------
        event : MarketEvent object
        """
        if event.type == 'MARKET':
            for s in self.symbol_list:
                bars = self.bars.get_latest_bars_values(s, "close",
                                                        N=self.long_window)
                bar_date = self.bars.get_latest_bar_datetime(s)

                if bars is not None:    #removed "and bars != []", depricated
                    short_sma = np.mean(bars[-self.short_window:])
                    long_sma = np.mean(bars[-self.long_window:])

                    symbol = s

                    dt = datetime.datetime.now(datetime.UTC)
                    sig_dir = ""

                    if short_sma > long_sma and self.bought[s] == "OUT":
                        print("LONG: %s" % bar_date)
                        sig_dir = "LONG"
                        signal = SignalEvent(1, symbol, dt, sig_dir, 1.0)
                        self.events.put(signal)
                        self.bought[s] = 'LONG'
                    elif short_sma < long_sma and self.bought[s] == "LONG":
                        print("SHORT: %s" % bar_date)
                        sig_dir = 'EXIT'
                        signal = SignalEvent(1, symbol, dt, sig_dir, 1.0)
                        self.events.put(signal)
                        self.bought[s] = 'OUT'




if __name__ == "__main__":
    csv_dir = 'ADD PATH HERE'
    symbol_list = ['AAPL']
    initial_capital = 100000.0
    heartbeat = 0.0
    start_date = datetime.datetime(2020, 4, 27)

    backtest = Backtest(csv_dir, symbol_list, initial_capital, heartbeat,
                        start_date, HistoricCSVDataHandler, SimulatedExecutionHandler,
                        Portfolio, MovingAverageCrossStrategy)
    backtest.simulate_trading()

