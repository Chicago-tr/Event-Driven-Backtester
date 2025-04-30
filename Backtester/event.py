#!/usr/bin/env python3
# -*- coding: utf-8 -*-

class Event(object):
    """
    Base parent class for events
    """
    pass


class MarketEvent(Event):
    """
    Receives new market update events
    """
    def __init__(self):
        """
        No Parameters,
        Identifies a market event
        """
        self.type = 'MARKET'

class SignalEvent(Event):
    """
    Handles event of sending a Signal from a Stategy object.
    This will be received by a Portfolio object and acted upon.
    """
    def __init__(self, strategy_id, symbol, datetime, signal_type, strength):
        """
        Parameters
        ----------
        strategy_id : ID for the strategy that generated the signal
        symbol (string): Ticker symbol
        datetime : Timestamp when signal was generated
        signal_type (string): 'SHORT' or 'LONG'
        strength : Adjustment factor 'suggestion' for scaling quantity at portfolio
        level. Good for pairs strategies
        """

        self.type = 'SIGNAL'
        self.strategy_id = strategy_id
        self.symbol = symbol
        self.datetime = datetime
        self.signal_type = signal_type
        self.strength = strength

class OrderEvent(Event):
    """
    Handles sending an Order to an execution system. Order will contain a symbol,
    a type (limit or market), quantity, and a direction.
    """
    def __init__(self, symbol, order_type, quantity, direction):
        """
        Parameters
        ----------
        symbol (string) : Ticker symbol
        order_type (string): 'LMT' or 'MKT' for Limit and Market orders
        quantity (int): Non-negative int representing quantity
        direction (string) : 'BUY' or 'SELL' for long and short
        """

        self.type = 'ORDER'
        self.symbol = symbol
        self.order_type = order_type
        self.quantity = quantity
        self.direction = direction

    def print_order(self):
        """
        Prints attributes of order
        """
        print("order: Symbol = %s, Type = %s, Quantity = %s, Direction = %s"
              % (self.symbol, self.order_type, self.quantity, self.direction)
              )

class FillEvent(Event):
    """
    Generated upon completion of an OrderEvent by ExecutionHandler. Describes
    the quantity and cost of a buy or sell as well as transaction costs.
    """
    def __init__(self, timeindex, symbol, exchange, quantity, direction,
                 fill_cost, commission=None):
        """
        Parameters
        ----------
        timeindex : Bar-resolution when order was filled
        symbol (string): Ticker symbol of filled order
        exchange : Exchange where order was filled
        quantity (int): Filled quantity
        direction (string): 'BUY' or 'SELL', direction of fill
        fill_cost : Holdings value (in dollars)
        commission (float) : Optional, if None: commission will be Interactive
        Brokers 'IBKR Pro-Fixed' rate of .005 per share or minimum 1.00
        """
        self.type = 'FILL'
        self.timeindex = timeindex
        self.symbol = symbol
        self.exchange = exchange
        self.quantity = quantity
        self.direction = direction
        self.fill_cost = fill_cost

        if commission is None:
            self.commission = self.calculate_commission()
        else:
            self.commission = commission

    def calculate_commission(self):
        """
        Calculates commission based on IBKR Pro-Fixed rate of .005 per share
        or a minimum of $1.00. Does not include other fees

        returns a float
        """
        if self.quantity * .005 > 1:
            return self.quantity * .005
        else:
            return 1.0




