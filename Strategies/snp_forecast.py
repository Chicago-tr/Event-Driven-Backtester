#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import datetime
import pandas as pd
from sklearn.discriminant_analysis import QuadraticDiscriminantAnalysis
# from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
# from sklearn.linear_model import LogisticRegression
from strategy import Strategy
from event import SignalEvent
from backtest import Backtest
from data import HistoricCSVDataHandler
from execution import SimulatedExecutionHandler
from portfolio import Portfolio
from create_lagged_series import create_lagged_series


class SPYDailyForecastStrategy(Strategy):
    """
    S&P500 forecast strategy. Uses a Quadratic Discriminant Analyser to predict
    returns for subsequent time period and use that prediction to generate signals
    """

    def __init__(self, bars, events):
        """
        Parameters
        ----------
        bars : Bar data from handler
        events : Events queue

        Returns
        -------
        Model

        """
        self.bars = bars
        self.symbol_list = self.bars.symbol_list
        self.events = events
        self.datetime_now = datetime.datetime.utcnow()

        self.model_start_date = datetime.datetime(2015,4,27) #Change these dates
        self.model_end_date = datetime.datetime(2025,4,25)   #Based on data
        self.model_start_test_date = datetime.datetime(2023,4,25)

        self.long_market = False       #Initializes as out of the market
        self.short_market = False
        self.bar_index = 0

        self.model = self.create_symbol_forecast_model()


    def create_symbol_forecast_model(self):
        # Create lagged series of S&P500 stock index
        snpret = create_lagged_series(self.symbol_list[0], self.model_start_date,
                                      self.model_end_date, lags=5)


        # Use prior 2 days returns as predictor values and direction as response
        X = snpret[["Lag1", "Lag2"]]
        y = snpret["Direction"]

        # Create training and test sets
        start_test = self.model_start_test_date



        X_train = X[X.index < start_test]
        X_test = X[X.index >= start_test]
        y_train = y[y.index < start_test]
        y_test = y[y.index >= start_test]



        model = QuadraticDiscriminantAnalysis()#Can replace model by changing this line
        model.fit(X_train, y_train)
        return model

    def calculate_signals(self, event):
        """
        Calculates SignalEvents based on market data.

        Parameters
        ----------
        events : Events queue object
        """
        sym = self.symbol_list[0]
        dt = self.datetime_now

        if event.type == 'MARKET':
            self.bar_index += 1
            if self.bar_index > 5:

                lags = self.bars.get_latest_bars_values(self.symbol_list[0],
                                                        "close", N=3)


                pred_series = pd.DataFrame({'Lag1': [lags[1]*100.0],  #change to df
                                         'Lag2' : [lags[2]*100.0]})   #lags required in lists




                pred = self.model.predict(pred_series)
                if pred > 0 and not self.long_market:
                    self.long_market = True
                    signal = SignalEvent(1, sym, dt, 'LONG', 1.0)
                    self.events.put(signal)

                if pred < 0 and self.long_market:
                    self.long_market = False
                    signal = SignalEvent(1, sym, dt, 'EXIT', 1.0)
                    self.events.put(signal)


if __name__ == "__main__":
    csv_dir = 'ADD PATH HERE'
    symbol_list = ['SPY']
    initial_capital = 100000.0
    heartbeat = 0.0
    start_date = datetime.datetime(2015,4,27)   #Change to fit dataset

    backtest = Backtest(csv_dir, symbol_list, initial_capital, heartbeat,
                        start_date, HistoricCSVDataHandler, SimulatedExecutionHandler,
                        Portfolio, SPYDailyForecastStrategy)

    backtest.simulate_trading()

