#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
note: no concept here of an indicator or filter but those would be good candidates
for a class heirachy as well. Those will be used directly in derived Strat. obj.

This hierachy consists of an abstract base class with a single virtual method for
generating SignalEvent objects
"""

from abc import ABCMeta, abstractmethod
import datetime
import queue
import numpy as np
import pandas as pd
from event import SignalEvent

class Strategy(object):
    """
    An abstract base class providing an interface for all strategy handeling obj.

    A Strategy subclass should generate Signal objects for particular symbols
    based on inputs of Bars from DataHandler objects

    Should work with both live and historic data since Strategy object obtains
    bar tuples from a queue object.
    """

    # __metaclass__ = ABCMeta

    @abstractmethod
    def calculate_signals(self):
        """
        method for calculating list of signals
        """
        raise NotImplementedError("Implement calculate_signals()")

