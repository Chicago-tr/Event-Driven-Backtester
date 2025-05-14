# Event Driven Backtester
Implementation of an event driven backtesting engine for algorithmic trading strategies found in "Successful Algorithmic Trading". Updated code to avoid deprecated features/packages.

## How it works
A brief overview of the backtester's class structure and how it executes.

The backtester is split into a number of components (class objects) that are brought together when a backtest class object is initialized. The following are the basic steps that make up the backtest.

```python
backtest = Backtest(csv_dir, symbol_list, initial_capital, heartbeat,
                    start_date, HistoricCSVDataHandler, SimulatedExecutionHandler,
                    Portfolio, SPYDailyForecastStrategy)

backtest.simulate_trading()
```
When initializing the backtest an events queue is created. This queue along with the passed arguments and component classes are stored as data attributes of the backtest.

```python
class Backtest(object):
  def __init__(self, csv_dir, symbol_list, initial_capital, heartbeat,
                 start_date, data_handler, execution_handler, portfolio, strategy):
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
```
The method _generate_trading_instances() is then called which creates the instances of the components of the backtester using the attributes of the backtest. This helps ensure consistency throughout the engine.

```python
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
```

The call to .simulate_trading() runs the backtest and outputs the results when finished
```python
def simulate_trading(self):
      """
      Simulates backtest and Outputs performance
      """
      self._run_backtest()
      self._output_performance()
```

The first step in ._run_backtest() is to check whether to continue running the backtest and if so to update a "data bar". A bar corresponds to a row in the csv data files containing information such as 'open', 'high', 'low', etc. 

```python
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
```

The call to .update_bars() will iterate over the list of symbols being tested and add the bar to a dictionary containing symbols as keys and bars as values. It then adds a "MARKET" event to the events queue. If there are no bars left self.continue_backtest is set to False and the test in the previous step will end in the backtest when its reached.

```python
def update_bars(self):
        """
        Moves latest bar to latest_symbol_data structure for every symbol
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
```

Returning to ._run_backtest() the next step is to handle all the events in the queue. The only event currently in queue is a Market event and so the following code is executed:

```python
if event.type == 'MARKET':
    self.strategy.calculate_signals(event)
    self.portfolio.update_timeindex(event)
```

The .calculate_signals() method is defined in the strategy class and should contain the conditions for generating a SignalEvent() (Enter long or short, Exit). If conditions are met this SignalEvent() is then added to the events queue. The .update_timeindex() method defined in the portfolio class is then called to record the state of the portfolio. With these calls finished the Market event has been handled and the loop checks for another event in the queue. Assuming a Signal event has been created the following code is executed:

```python
elif event.type == 'SIGNAL':
    self.signals += 1
    self.portfolio.update_signal(event)
```

.update_signal() will take the Signal event object, create an Order event, and add it to the queue. This Order event will contain information such as the symbol, order type, quantity, and direction of the order. This step is also where considerations such as risk management could be implemented to affect the order.

With the Order event in the queue the execution_handler class is utilized.

```python
elif event.type == 'ORDER':
    self.orders += 1
    self.execution_handler.execute_order(event)
```
.execute_order() then uses the execution handler to submit the order to an exchange and create a Fill event containing information about the order when its filled. The execution handler will need to be customized to the exchange and be able to retrieve the order fill information. For backtesting purposes the Fill order event is just created directly and the event put into the queue.

```python
if event.type == 'ORDER':
    fill_event = FillEvent( datetime.datetime.utcnow(), event.symbol,
                           'Exchange Name', event.quantity, event.direction, None)

    self.events.put(fill_event)
```

Finally, with another event (the Order) cleared from the queue, the Fill event is handled next.
```python
elif event.type == 'FILL':
      self.fills += 1
      self.portfolio.update_fill(event)
```
This step just updates the portfolio record with information pertaining to the filled order.
With no events left in the queue the final step of the outer loop is reached.
```time.sleep(self.heartbeat)``` is called using the time period defined with the heartbeat argument. For a backtest this value is 0 since all the data is already collected and there's no need to wait.

The outer loop then repeats with the next bar of market data until all bars are exhausted and the performance of the backtest is output using the data recorded in the portfolio class.

