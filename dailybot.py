import pandas as pd
import numpy as np
import yfinance
import mplfinance
import matplotlib.dates as mpl_dates
import matplotlib.pyplot as plt
from datetime import datetime
from discord_webhook import DiscordWebhook
from collections import OrderedDict
import time
import csv
import alpaca_trade_api as tradeapi
from apscheduler.schedulers.blocking import BlockingScheduler

def serial_date_to_string(srl_no):
  new_date = datetime.datetime(1970,1,1,0,0) + datetime.timedelta(srl_no - 1)
  return new_date.strftime("%Y-%m-%d")

def isSupport(df,i):
  support = df['Low'][i] < df['Low'][i-1]  and df['Low'][i] < df['Low'][i+1] \
  and df['Low'][i+1] < df['Low'][i+2] and df['Low'][i-1] < df['Low'][i-2]
  return support

def isResistance(df,i):
  resistance = df['High'][i] > df['High'][i-1]  and df['High'][i] > df['High'][i+1] \
  and df['High'][i+1] > df['High'][i+2] and df['High'][i-1] > df['High'][i-2]
  return resistance

def is_bearish_candle(candle):
  return candle['Close'] < candle['Open']

def is_bullish_candle(candle):
  return candle['Close'] > candle['Open']

def is_bullish_engulfing(candles):
  current_day = candles[-1]
  previous_day = candles[-2]
  if is_bearish_candle(previous_day) \
      and is_bullish_candle(current_day) \
      and float(current_day['Close']) >= float(previous_day['Open']) \
      and float(current_day['Open']) <= float(previous_day['Close']):
      return True
  return False

def is_bearish_engulfing(candles):
  current_day = candles[-1]
  previous_day = candles[-2]
  if is_bullish_candle(previous_day) \
      and is_bearish_candle(current_day) \
      and float(current_day['Open']) >= float(previous_day['Close']) \
      and float(current_day['Close']) <= float(previous_day['Open']):
      return True
  return False

def closest_support(recent_close, supports):
  if (len(supports) > 0) == True:
    closestsup = supports[0][0]
    for x in range(len(supports)):
      if recent_close-supports[x][0] < recent_close-closestsup:
        closestsup = supports[x][0]
    return closestsup

def closest_resistance(recent_close, resistances):
  if (len(resistances) > 0) == True:
    closestres = resistances[0][0]
    for x in range(len(resistances)):
      if recent_close-resistances[x][0] < abs(recent_close-closestres):
        closestres = resistances[x][0]
    return closestres

def sma_20(candles):
  total = 0
  for i in range(1, 20):
    total += candles[-i]['Close']
  total /= 20
  return round(total, 2)

def sma_50(candles):
  total = 0
  for i in range(1, 50):
    total += candles[-i]['Close']
  total /= 50
  return round(total, 2)

def golden_cross(candles):
  sma20_1 = sma_20(candles)
  sma50 = sma_50(candles)
  candles.pop()
  sma20_2 = sma_20(candles)
  if sma20_2 < sma20_1 \
    and sma20_2 < sma50 \
    and sma20_1 > sma50:
    return True
  return False

def death_cross(candles):
  sma20_1 = sma_20(candles)
  sma50 = sma_50(candles)
  candles.pop()
  sma20_2 = sma_20(candles)
  if sma20_2 > sma20_1 \
    and sma20_2 > sma50 \
    and sma20_1 < sma50:
    return True
  return False

def isFarFromLevel(l):
  return np.sum([abs(l-x) < s  for x in levels]) == 0

def rsi(candles):
  avggain = 0
  avgloss = 0
  downdays = 0
  updays = 0
  for x in range(1, 14):
    change = (candles[-x-1]['Close']-candles[-x]['Close'])
    if change >= 0:
      avggain += change
      updays += 1
    elif change <= 0:
      avgloss -= change
      downdays += 1
  recent_close = candles[-1]['Close']
  avggain /= recent_close
  avgloss /= recent_close
  avggain /= updays
  avgloss /= downdays
  rsi = 100-((100)/(1+(avggain/avgloss)))
  return round(rsi, 2)

def call_stock(ticker, last):
  api = tradeapi.REST(
    'PKZRTA8WA85F1KY2KSLV',
    'mHzZ3UbSZTllhwAh4OanYVFJkrDvzq9azUpEHTyz',
    'https://paper-api.alpaca.markets', api_version='v2')
  no_of_shares = int(5000/last)
  #position = api.get_position(ticker)
  #if int(position.qty) < 0:
    #no_of_shares -= position.qty
    #add this to sell order +int(position.qty)
  order = api.submit_order(ticker, no_of_shares, 'buy', 'market', 'day')
  #sell_price = last * 1.02
  #order = api.submit_order(ticker, (no_of_shares), 'sell', 'limit', 'gtc', sell_price)

def short_stock(ticker, last):
  api = tradeapi.REST(
    'PKZRTA8WA85F1KY2KSLV',
    'mHzZ3UbSZTllhwAh4OanYVFJkrDvzq9azUpEHTyz',
    'https://paper-api.alpaca.markets', api_version='v2')
  no_of_shares = int(5000/last)
  #position = api.get_position(ticker)
  #if int(position.qty) > 0:
    #no_of_shares += position.qty
    #add this to sell order -int(position.qty)
  order = api.submit_order(ticker, no_of_shares, 'sell', 'market', 'day')
  #sell_price = last * 0.98
  #order = api.submit_order(ticker, (no_of_shares), 'buy', 'limit', 'gtc', sell_price)

def close_bullish(ticker, shareno):
  api = tradeapi.REST(
    'PKZRTA8WA85F1KY2KSLV',
    'mHzZ3UbSZTllhwAh4OanYVFJkrDvzq9azUpEHTyz',
    'https://paper-api.alpaca.markets', api_version='v2')
  order = api.submit_order(ticker, no_of_shares, 'sell', 'market', 'day')

def close_bearish(ticker, shareno):
  api = tradeapi.REST(
    'PKZRTA8WA85F1KY2KSLV',
    'mHzZ3UbSZTllhwAh4OanYVFJkrDvzq9azUpEHTyz',
    'https://paper-api.alpaca.markets', api_version='v2')
  order = api.submit_order(ticker, no_of_shares, 'buy', 'market', 'day')

def job_function():
  plt.rcParams['figure.figsize'] = [12, 7]
  plt.rc('font', size=14)
  companies = csv.reader(open('companies.csv'))
  names = []
  open_positions = []
  for company in companies:
    symbol, name = company
    names.append(symbol)

  for name in names:
    time.sleep(0.01)
    print(name)
    ticker = yfinance.Ticker(name)
    df = ticker.history(interval="1d", period="3mo")
    df['Date'] = pd.to_datetime(df.index)
    df['Date'] = df['Date'].apply(mpl_dates.date2num)
    df = df.loc[:,['Date', 'Open', 'High', 'Low', 'Close']]
    candles = [OrderedDict(row) for i, row in df.iterrows()]
    

    levels = []
    plainlevels = []
    for i in range(2,df.shape[0]-2):
      if isSupport(df,i):
        levels.append((df['Date'][i],df['Low'][i]))
        plainlevels.append(df['Low'][i])
      elif isResistance(df,i):
        levels.append((df['Date'][i],df['High'][i]))
        plainlevels.append(df['High'][i])
    s =  np.mean(df['High'] - df['Low'])
    recent_close = candles[-1]['Close']
    supports = []
    resistances = []
    for i in plainlevels:
      difference = round(recent_close-i, 2)
      if i < recent_close:
        supports.append((i, difference))
      elif i > recent_close:
        round(i-recent_close, 2)
        resistances.append((i, difference))
    closestsup = closest_support(recent_close, supports)
    closestres = closest_resistance(recent_close, resistances)
    if closestres is not None:
      respoint = round(closestres, 2)
    if closestsup is not None:
      suppoint = round(closestsup, 2)
    webhookurl = 'https://discord.com/api/webhooks/838861523702906922/tGHcememPrzovcZtRAOZmg0w8GwF59sgZUP-wKuTHJ-cDHq9XXC8wvNcI1zqoX5rloW5'
    if is_bearish_engulfing(candles):
      webhook = DiscordWebhook(url=webhookurl, content='Bearish Engulfing on ' + str(name) + ', Support: ' + str(suppoint) + ', Resistance: ' + str(respoint))
      response = webhook.execute()
      #webhook = DiscordWebhook(url=webhookurl, content='!c2 ' + str(name) + ' t=c i=15m')
      #response = webhook.execute()
      #short_stock(name, recent_close)
      shareno = 0-int(5000/recent_close)
      position = []
      position.append(name)
      position.append(shareno)
      open_positions.append(position)
      print("Bearish Engulfing on "+ str(name))
    if is_bullish_engulfing(candles):
      webhook = DiscordWebhook(url=webhookurl, content='Bullish Engulfing on ' + str(name) + ', Support: ' + str(suppoint) + ', Resistance: ' + str(respoint))
      response = webhook.execute()
      #webhook = DiscordWebhook(url=webhookurl, content='!c2 ' + str(name) + ' t=c i=15m')
      #response = webhook.execute()
      #call_stock(name, recent_close)
      shareno = int(5000/recent_close)
      position = []
      position.append(name)
      position.append(shareno)
      open_positions.append(position)
      print("Bullish Engulfing on "+ str(name))
    """if golden_cross(candles):
      #webhook = DiscordWebhook(url=webhookurl, content='Golden Cross on ' + str(name))
      #response = webhook.execute()
      #webhook = DiscordWebhook(url=webhookurl, content='!c2 ' + str(name) + ' t=c i=15m')
      #response = webhook.execute()
      #call_stock(name, recent_close)
      #shareno = int(5000/recent_close)
      #position = []
      position.append(name)
      position.append(shareno)
      open_positions.append(position)
      print("Golden Cross on "+ str(name))
    if death_cross(candles):
      #webhook = DiscordWebhook(url=webhookurl, content='Death Cross on ' + str(name))
      #response = webhook.execute()
      #webhook = DiscordWebhook(url=webhookurl, content='!c2 ' + str(name) + ' t=c i=15m')
      #response = webhook.execute()
      #call_stock(name, recent_close)
      shareno = 0-int(5000/recent_close)
      position = []
      position.append(name)
      position.append(shareno)
      open_positions.append(position)
      print("Death Cross on "+ str(name))"""
  positions = csv.reader(open('positions.csv'))
  for company in positions:
    symbol, pos = company
    print(symbol)
    ticker = yfinance.Ticker(symbol)
    df = ticker.history(interval="1d", period="3mo")
    df['Date'] = pd.to_datetime(df.index)
    df['Date'] = df['Date'].apply(mpl_dates.date2num)
    df = df.loc[:,['Date', 'Open', 'High', 'Low', 'Close']]
    candles = [OrderedDict(row) for i, row in df.iterrows()]
    if int(pos) > 0:
      if is_bearish_candle(candles):
        close_bullish(symbol, pos)
      else:
        open_positions.append(symbol)
        open_positions.append(pos)
    if int(pos) < 0:
      if is_bullish_candle(candles):
        close_bearish(symbol, pos)
      else:
        open_positions.append(symbol)
        open_positions.append(pos)
  df = pd.DataFrame(open_positions)
  df.to_csv('positions.csv', index=False)

#def sell_stocks():
  
#sched = BlockingScheduler()
job_function()

#sched.add_job(job_function, 'cron', day_of_week='mon-fri', hour=9, minute=30)
#sched.add_job(sell_stocks, 'cron', day_of_week='mon-fri', hour='8-13')


#sched.start()
"""
companies = csv.reader(open('positions.csv'))
names = []
open_positions = []
for company in companies:
  symbol, name = company
  names.append(company)
for position in names:
  ticker = yfinance.Ticker(position[0])
  df = ticker.history(interval="1d", period="3mo")
  df['Date'] = pd.to_datetime(df.index)
  df['Date'] = df['Date'].apply(mpl_dates.date2num)
  df = df.loc[:,['Date', 'Open', 'High', 'Low', 'Close']]
  candles = [OrderedDict(row) for i, row in df.iterrows()]
  print(candles)
  if int(position[1]) > 0:
    if is_bearish_candle(candles):
      #sell_call(position[0], int(position[1]))
      print("sell call on "+ str(positions[0]))
    else:
      open_positions.append(position)
  if int(position[1]) < 0:
    if is_bullish_candle(candles):
      #sell_short(position[0], position[1])
      print("sell short on "+ str(positions[0]))
    else:
      open_positions.append(position)
print(open_positions)"""