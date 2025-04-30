#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd


def create_lagged_series(symbol, start_date, end_date, lags=5):
    """
    Creates Pandas DataFrame that stores % return of closing value of a stock
    obtained from Nasdaq, along with some other lagged returns from prior
    trading days (lags defaults to 5 days). Trading vol. and Direction from
    previous day are included as well.

    Returns
    -------
    Dataframe, lagged time series

    """
    # ts = DataReader(symbol, "nasdaq", start_date-datetime.timedelta(days=365),
    #                 end_date)
    ts = pd.read_csv('ADD PATH HERE')
    ts['Date'] = pd.to_datetime(ts['Date'])
    ts = ts.set_index('Date')


    #Create new lagged DataFrame
    tslag = pd.DataFrame(index=ts.index)
    tslag["Today"] = ts["Close/Last"]
    tslag ["Volume"] = ts["Volume"]

    #Create shifted lag series of prior trading period close values
    for i in range(0, lags):
        tslag["Lag%s" % str(i+1)] = ts["Close/Last"].shift(i+1)

    #Create the returns DataFrame
    tsret = pd.DataFrame(index=tslag.index)
    tsret["Volume"] = tslag["Volume"]
    tsret["Today"] = tslag["Today"].pct_change()*100.0

    #If any values for % returns equals 0, set them to small number
    #Do this to stop issues with QDA model

    for i,x in enumerate(tsret["Today"]):
        if (abs(x) < 0.0001):
            tsret["Today"][i] = 0.0001

    #Create lagged % returns columns
    for i in range(0, lags):
        tsret["Lag%s" % str(i+1)] = tslag["Lag%s" % str(i+1)].pct_change()*100.0

    #Create the Direction column (+1 or -1) indicating an up or down day
    tsret["Direction"] = np.sign(tsret["Today"])
    tsret = tsret[tsret.index >= start_date]

    return tsret
