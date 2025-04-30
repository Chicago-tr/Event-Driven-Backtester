#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Portfolio object will keep track of positions within a portfolio and generate
orders from signals. It should handle SignalEvent objects, generate OrderEvent objects,
and interpret FillEvent objects.

Portfolio Management System should keep track of all current market positions
and market value of the holdings. Should be thought of as an estimate.
"""

import numpy as np
import pandas as pd

def create_sharpe_ratio(returns, periods=252):
    """
    Parameters
    ----------
    returns : Pandas Series representing period % returns.
    periods : default is Daily (252). Houry (252* 6.5), Minute(252*6.5*60)

    Returns
    -------
    Sharpe Ratio
    """
    return (np.sqrt(periods) * ((np.mean(returns)))) / np.std(returns)

def create_drawdowns(pnl):
    """
    Calculates biggest peak-to-trough drawdown on the PnL curve and its duration.

    Parameters
    ----------
    pnl : Pandas Series representing period % returns

    Returns
    -------
    drawdown, duration
    """
    hwm = [0]
    idx = pnl.index
    drawdown = pd.Series(index = idx)
    duration = pd.Series(index = idx)

    for t in range(1, len(idx)):
        hwm.append(max(hwm[t-1], pnl.iloc[t]))
        drawdown.iloc[t]= (hwm[t]-pnl.iloc[t])
        duration.iloc[t]= (0 if drawdown.iloc[t] ==0 else duration.iloc[t-1]+1)
    return drawdown, drawdown.max(), duration.max()

