#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from abc import ABCMeta, abstractmethod
import datetime
import os, os.path

import numpy as np
import pandas as pd

from event import MarketEvent

"""
Goal is to have as much similarity as possible between backtester and live
execution code. Thus, Strategy object that generates Signals and Portfolio object
which makes Orders based on the Signals should use an identical interface to a
market feed whether backtesting or running live.

DataHandler object will give subclasses structure for providing market data to
rest of system, this should allow for customizing subclasses to data sources as
necessary without needing to change everything else
"""


class DataHandler(object):
    """
    Abstract base class providing structure for subsequent data handers (live or historic)

    Goal of subclasses is to generate and output a set of bars (Open-High-Low-
    Close-Volume-OpenInterest)

    Replicates a live strategy where current market data is processed. A historic
    and live system should be treated identically by the rest of the system
    """
    # __metaclass__ = ABCMeta()

    #decorator signifies the method must be overridden by a concrete subclass
    @abstractmethod
    def get_latest_bar(self, symbol):
        """
        Parameters
        ----------
        symbol (str) : Ticker symbol

        Returns
        -------
        Last bar updated
        """
        raise NotImplementedError("Implement get_latest_bar()")

    @abstractmethod
    def get_latest_bars(self, symbol, N=1):
        """
        Parameters
        ----------
        symbol (str) : Ticker symbol
        N (int) :optional, Number of bars updated to return
            default = 1
        Returns
        -------
        Last N bars updated
        """
        raise NotImplementedError("Implement get_latest_bars()")

    @abstractmethod
    def get_latest_bar_datetime(self, symbol):
        """
        Parameters
        ----------
        symbol (str) : Ticker symbol

        Returns
        -------
        Python datetime object for last bar
        """
        raise NotImplementedError("Implement get_latest_bar_datetime()")

    @abstractmethod
    def get_latest_bar_value(self, symbol, val_type):
        """
        Parameters
        ----------
        symbol (str) : Ticker symbol
        val_type (str) : Which val to return ('Open', 'High', 'Close', etc)

        Returns
        -------
        One of either Open, High, Low, Close, Volume, or OI from last bar.

        """
        raise NotImplementedError("Implement get_latest_bar_value()")

    @abstractmethod
    def get_latest_bars_values(self, symbol, val_type, N=1):
        """
        Parameters
        ----------
        symbol (str) : Ticker symbol
        val_type (str) : Which val to return ('Open', 'High', 'Close', etc)
        N (int): optional, N (int) : Number of bars updated to return
            default = 1
        Returns
        -------
        The latest N bar values from the symbols or N-k if less are available
        """
        raise NotImplementedError("Implement get_latest_bars_values()")

    @abstractmethod
    def update_bars(self):
        """
        Moves latest bars to the bars_queue for each symbol
        in a tuple of format OHLCVI: (datetime, open, high, low,
        close, volume, open interest)
        """
        raise NotImplementedError("Implement update_bars()")

class HistoricCSVDataHandlerHFT(DataHandler):
    """
    For reading CSV files for each symbol requested from disk and providing a
    structure to obtain the latest bar in a manner that should replicate a live
    trading interface
    """
    def __init__(self, events, csv_dir, symbol_list):
        """
        Parameters
        ----------
        events : The Event Queue
        csv_dir (str) : Directory path to CSV files
        symbol_list (list) : A list of symbol strings
        """
        self.events = events
        self.csv_dir = csv_dir
        self.symbol_list = symbol_list
        self.symbol_data = {}
        self.latest_symbol_data = {}
        self.continue_backtest = True
        self._open_convert_csv_files()

    def _open_convert_csv_files(self):
        """
        Opens CSV files from the data directory,converts them into pandas
        DataFrames within a symbol dictionary.
        For this handler it will be assumed that the data is
        taken from Yahoo. Thus its format will be respected.
        """
        comb_index = None

        for s in self.symbol_list:
            # Load the CSV file with no header information, indexed on date
            self.symbol_data[s] = pd.io.parsers.read_csv(
                os.path.join(self.csv_dir, '%s.csv' % s),
                header=0, index_col=0, parse_dates=True,

                #names list edited for Nasdaq source
                names=['datetime', 'open', 'high','low', 'close', 'volume']
            ).sort_values(by='datetime') #Updated sorting method


            # Index combined to pad forward values
            if comb_index is None:
                comb_index = self.symbol_data[s].index
            else:
                comb_index.union(self.symbol_data[s].index)

            # Set the latest symbol_data to None
            self.latest_symbol_data[s] = []

        # Reindex the dataframes
        for s in self.symbol_list:
            self.symbol_data[s] = self.symbol_data[s].\
                reindex(index=comb_index, method='pad').iterrows()

    def _get_new_bar(self, symbol):
        """
        Parameters
        ----------
        symbol (str): Ticker symbol

        Returns
        -------
        Latest bar from data feed
        """
        for bar in self.symbol_data[symbol]:
            yield bar

    def get_latest_bar(self, symbol):
        """
        Parameters
        ----------
        symbol (str): Ticker symbol

        Returns
        -------
        Last bar from the latest_symbol list
        """
        try:
            bars_list = self.latest_symbol_data[symbol]
        except KeyError:
            print(symbol,"not available in historic data set")
            raise
        else:
            return bars_list[-1]

    def get_latest_bars(self, symbol, N=1):
        """
        Parameters
        ----------
        symbol (str): Ticker symbol
        N (int): optional, number of bars to return

        Returns
        -------
        Last N bars from the latest_symbol list, or N-k if N not available
        """
        try:
            bars_list = self.latest_symbol_data[symbol]
        except KeyError:
            print(symbol,"not available in historic data set")
            raise
        else:
            return bars_list[-N:]

    def get_latest_bar_datetime(self, symbol):
        """
        Parameters
        ----------
        symbol (str): Ticker symbol

        Returns
        -------
        Python datetime object for last bar.
        """
        try:
            bars_list = self.latest_symbol_data[symbol]
        except KeyError:
            print(symbol,"not available in historic data set")
            raise
        else:
            return bars_list[-1][0]

    def get_latest_bar_value(self, symbol, val_type):
        """
        Parameters
        ----------
        symbol (str): Ticker symbol
        val_type (str): val_type (str) : Which val to return ('open', 'high',
                                                              'close', etc)

        Returns
        -------
        Returns one chosen value from pandas Bar series object.
        """
        try:
            bars_list = self.latest_symbol_data[symbol]
        except KeyError:
            print(symbol,"not available in historic data set")
            raise
        else:
            return getattr(bars_list[-1][1], val_type)

    def get_latest_bars_values(self, symbol, val_type, N=1):
        """
        Parameters
        ----------
        symbol (str): Ticker symbol
        val_type (str): val_type (str) : Which val to return ('Open', 'High',
                                                              'Close', etc)
        N (int): optional, number of bars values to return
        Returns
        -------
        Returns last N chosen values from latest_symbol list, N-k if N not avail.
        """
        try:
            bars_list = self.get_latest_bars(symbol, N)
            # print(bars_list)
        except KeyError:
            print(symbol,"not available in historic data set")
            raise

        else:
            #getattr() function lets you obtain the value of an object's attribute
            return np.array([getattr(b[1], val_type) for b in bars_list])

    def update_bars(self):
        """
        Moves latest bar to latest_symbol_data strcture for every symbol
        in symbol list and creates a Market Event that gets added to queue
        """
        for symbol in self.symbol_list:
            try:
                bar = next(self._get_new_bar(symbol))
            except StopIteration:
                self.continue_backtest = False
            else:
                if bar is not None:
                    self.latest_symbol_data[symbol].append(bar)
        self.events.put(MarketEvent())

