#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import print_function
import datetime
import pprint
import queue
import time

"""
Backtest object will cover event-handling logic and tie together the rest of
the classes. It will use nested while-loops to handle events in the EventQueue
object. The outer while-loop controls the temporal resolution of the system,
in a live env. this value will be a positive number. The market data and positions
will be updated on this timeframe.
For backtesting this value can be set to 0 regardless of strategy frequency
since the data is already available (since its historic)
Inner while-loop interprets the signals directs them depending on the event type.
Event Queue will be continually populated and depopulated with events (it is event-driven)
"""


class Backtest(object):
    """
    Encapsulates settings and components for carrying out backtests.
    """
    def __init__(self, csv_dir, symbol_list, initial_capital, heartbeat,
                 start_date, data_handler, execution_handler, portfolio, strategy):
        """
        Initializes the backtest.

        Parameters
        ----------
        csv_dir : Hard root to the CSV data directory
        symbol_list : List of symbol strings
        initial_capital : Starting capital of the portfolio
        heartbeat : 'Heartbeat' of the backtest in seconds
        start_date : Start datetime of the strategy
        data_handler : (Class) Handles market data feed
        execution_handler : (Class) Handles orders/fills for trades.
        portfolio : (Class) Keeps track of current and prior portfolio positions.
        strategy : (Class) Generates signals based on market data
        """
        self.csv_dir = csv_dir
        self.symbol_list = symbol_list
        self.initial_capital = initial_capital
        self.heartbeat = heartbeat
        self.start_date = start_date
        self.data_handler_cls = data_handler
        self.execution_handler_cls = execution_handler
        self.portfolio_cls = portfolio
        self.strategy_cls = strategy

        self.events = queue.Queue()

        self.signals = 0
        self.orders = 0
        self.fills = 0
        self.num_strats = 1

        self._generate_trading_instances()

    def _generate_trading_instances(self):
        """
        Generates trading instance objects based on their class types.
        """
        print("Creating DataHandler, Strategy, Portfolio and ExecutionHandler")
        self.data_handler = self.data_handler_cls(self.events,self.csv_dir,
        self.symbol_list)
        self.strategy = self.strategy_cls(self.data_handler, self.events)
        self.portfolio = self.portfolio_cls(self.data_handler, self.events,
                                            self.start_date, self.initial_capital)
        self.execution_handler = self.execution_handler_cls(self.events)

    def _run_backtest(self):
        """
        Runs backtest.
        """
        i = 0
        while True:
            i += 1

            #Update market bars
            if self.data_handler.continue_backtest == True:
                self.data_handler.update_bars()
            else:
                break

            #Handle events
            while True:
                try:
                    #.get(False) stops blocking behavior in retrieving from queue
                    event = self.events.get(False)
                except queue.Empty:
                    break
                else:
                    if event is not None:
                        if event.type == 'MARKET':
                            self.strategy.calculate_signals(event)
                            self.portfolio.update_timeindex(event)

                        elif event.type == 'SIGNAL':
                            self.signals += 1
                            self.portfolio.update_signal(event)

                        elif event.type == 'ORDER':
                            self.orders += 1
                            self.execution_handler.execute_order(event)

                        elif event.type == 'FILL':
                            self.fills += 1
                            self.portfolio.update_fill(event)



            time.sleep(self.heartbeat)

    def _output_performance(self):
        """
        Outputs performance summary of the backtested strategy.
        """
        self.portfolio.create_equity_curve_dataframe()

        print("Creating summary stats...")
        stats = self.portfolio.output_summary_stats()

        print("Creating equity curve...")
        print(self.portfolio.equity_curve.tail(10))
        pprint.pprint(stats)


        print("Signals: %s" % self.signals)
        print("Orders: %s" % self.orders)
        print("Fills: %s" % self.fills)

        self.portfolio.equity_curve.to_csv('Equity.csv')



    def simulate_trading(self):
        """
        Simulates backtest and Outputs performance
        """
        self._run_backtest()
        self._output_performance()
