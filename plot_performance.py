#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os.path

import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

if __name__ == "__main__":
    data = pd.io.parsers.read_csv("equity.csv", header=0, parse_dates=True,
                                  index_col=0).sort_values(by='datetime')


    #Plot three charts: equity curve, period returns, drawdowns
    fig = plt.figure()
    #Setting outer colour
    fig.patch.set_facecolor('white')

    #Plot equity curve
    ax1 = fig.add_subplot(311, ylabel='Portfolio value, %')
    data['equity_curve'].plot(ax=ax1, color='blue', lw=2.)
    plt.grid(True)

    #Plot the returns
    ax2 = fig.add_subplot(312, ylabel='Period returns, %')
    data['returns'].plot(ax=ax2, color='black', lw=2.)
    plt.grid(True)

    #Plot the returns
    ax3 = fig.add_subplot(313, ylabel='Drawdowns, %')
    data['drawdown'].plot(ax=ax3, color='red', lw=2.)
    plt.grid(True)

    plt.show()
