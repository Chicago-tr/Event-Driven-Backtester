#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
"""

import datetime

import numpy as np
import pandas as pd
import statsmodels.api as sm

from strategy import Strategy
from event import SignalEvent
from backtest import Backtest
from hft_data import HistoricCSVDataHandlerHFT
from hft_portfolio import PortfolioHFT
from execution import SimulatedExecutionHandler


class IntradayOLSMRStrategy(Strategy):
    """
    Use ordinary least sqaures to perform rolling linear regression to determine
    hedge ratio between two securities. Z-score of the residuals time series
    is calculated in a rolling fashion. If it exceeds an interval of thresholds
    a long/short signal pair are generated (from high threshold) or an exit
    signal pair are generated (low threshold)
    """
    #Can change zscores to set different interval thresholds
    def __init__(self, bars, events, ols_window=100, zscore_low=0.5,
                 zscore_high=3.0):
        """
        Parameters
        ----------
        bars : DataHandler object providing bar information
        events : Event Queue object
        ols_window : optional window for ols. The default is 100.
        zscore_low : optional, zscore low threshold. The default is 0.5
        zscore_high : optional, zscore high threshold The default is 3.0
        """
        self.bars = bars
        self.symbol_list = self.bars.symbol_list
        self.events = events
        self.ols_window = ols_window
        self.zscore_low = zscore_low
        self.zscore_high = zscore_high

        self.pair = ('SPY', 'QQQ')
        self.datetime = datetime.datetime.now(datetime.UTC)

        self.long_market = False
        self.short_market = False


    def calculate_xy_signals(self, zscore_last):
        """
        Calculates x, y signal pairings to be sent to the signal generator.

        Parameters
        ----------
        zscore_last : Current zscore to test

        Returns
        -------
        Signal events corresponding to the securities pair (x,y)
        If no conditions met, then pair of None values returned
        """

        y_signal = None
        x_signal = None
        p0 = self.pair[0]
        p1 = self.pair[1]
        dt = self.datetime
        hr = abs(self.hedge_ratio)

        #If long the market and below the negative of high zscore threshold
        if zscore_last <= -self.zscore_high and not self.long_market:
            self.long_market = True
            y_signal = SignalEvent(1, p0, dt, 'LONG', 1.0)
            x_signal = SignalEvent(1, p1, dt, 'SHORT', hr)

        #If long the market and between the abs. value of low zscore threshold
        if abs(zscore_last) <= self.zscore_low and self.long_market:
            self.long_market = False
            y_signal = SignalEvent(1, p0, dt, 'EXIT', 1.0)
            x_signal = SignalEvent(1, p1, dt, 'EXIT', 1.0)

        #If short the market and above high zscore threshold
        if zscore_last >= self.zscore_high and not self.short_market:
            self.short_market = True
            y_signal = SignalEvent(1, p0, dt, 'SHORT', 1.0)
            x_signal = SignalEvent(1, p1, dt, 'LONG', hr)

        #If short the market and between abs. value of low zscore threshold
        if abs(zscore_last) <= self.zscore_low and self.short_market:
            self.short_market = False
            y_signal = SignalEvent(1, p0, dt, 'EXIT', 1.0)
            x_signal = SignalEvent(1, p1, dt, 'EXIT', 1.0)

        return y_signal, x_signal

    def calculate_signals_for_pairs(self):
        """
        Generates new set of signals from the mean reversion strategy.
        Calculates hedge ratio between pair.
        """
        y = self.bars.get_latest_bars_values(self.pair[0], "close",
                                             N=self.ols_window)
        x = self.bars.get_latest_bars_values(self.pair[1], "close",
                                             N=self.ols_window)

        if y is not None and x is not None:
            #Check all window periods are available
            if len(y) >= self.ols_window and len(x) >= self.ols_window:
                #Calculate current hedge ratio using OLS
                self.hedge_ratio = sm.OLS(y, x).fit().params[0]

                #Calculate the current zscore of residuals
                spread = y - self.hedge_ratio * x
                zscore_last = ((spread - spread.mean())/spread.std())[-1]

                #Calculate signals and add to events queue
                y_signal, x_signal = self.calculate_xy_signals(zscore_last)
                if y_signal is not None and x_signal is not None:
                    self.events.put(y_signal)
                    self.events.put(x_signal)

    def calculate_signals(self, event):
        """
        Parameters
        ----------
        event : Event Queue object
        """
        if event.type == 'MARKET':
            self.calculate_signals_for_pairs()

if __name__ == "__main__":
    csv_dir = '/Users/johnurban/quant projects/'
    symbol_list = ['SPY', 'QQQ']
    initial_capital = 100000.0
    heartbeat = 0.0
    start_date = datetime.datetime(2022,9,30,4,0,0)

    backtest = Backtest(csv_dir, symbol_list, initial_capital, heartbeat,
                        start_date, HistoricCSVDataHandlerHFT,
                        SimulatedExecutionHandler, PortfolioHFT, IntradayOLSMRStrategy)
    backtest.simulate_trading()








