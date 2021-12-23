import time
import pyupbit
import datetime
import schedule
from fbprophet import Prophet
import requests


access = "1"
secret = "2"
myToken = "3"


def post_message(token, channel, text):
    """슬랙 메시지 전송"""
    response = requests.post("https://slack.com/api/chat.postMessage",
        headers={"Authorization": "Bearer "+token},
        data={"channel": channel,"text": text}
    )

def get_target_price(ticker, k):
    """변동성 돌파 전략으로 매수 목표가 조회"""
    df = pyupbit.get_ohlcv(ticker, interval="day", count=2)
    target_price = df.iloc[0]['close'] + (df.iloc[0]['high'] - df.iloc[0]['low']) * k
    # print("target price = {} " .format(target_price))
    return target_price

def get_start_time(ticker):
    """시작 시간 조회"""
    df = pyupbit.get_ohlcv(ticker, interval="day", count=1)
    start_time = df.index[0]
    return start_time

def get_balance(ticker):
    """잔고 조회"""
    balances = upbit.get_balances()
    for b in balances:
        if b['currency'] == ticker:
            if b['balance'] is not None:
                return float(b['balance'])
            else:
                return 0
    return 0

def get_current_price(ticker):
    """현재가 조회"""
    return pyupbit.get_orderbook(ticker=ticker)["orderbook_units"][0]["ask_price"]

predicted_close_price = 0
def predict_price(ticker):
    """Prophet으로 당일 종가 가격 예측"""
    global predicted_close_price
    df = pyupbit.get_ohlcv(ticker, interval="minute60")
    df = df.reset_index()
    df['ds'] = df['index']
    df['y'] = df['close']
    data = df[['ds','y']]
    model = Prophet()
    model.fit(data)
    future = model.make_future_dataframe(periods=24, freq='H')
    forecast = model.predict(future)
    closeDf = forecast[forecast['ds'] == forecast.iloc[-1]['ds'].replace(hour=9)]
    if len(closeDf) == 0:
        closeDf = forecast[forecast['ds'] == data.iloc[-1]['ds'].replace(hour=9)]
    closeValue = closeDf['yhat'].values[0]
    predicted_close_price = closeValue
    print("*"*50)
    print("Predict price = {} " .format(predicted_close_price))
predict_price("KRW-BTC")
schedule.every().hour.do(lambda: predict_price("KRW-BTC"))

# 로그인
upbit = pyupbit.Upbit(access, secret)
print("*"*50)
print("autotrade start")
print("*"*50)
# 시작 메세지 슬랙 전송
post_message(myToken,"#python", "autotrade start")

# 자동매매 시작
while True:
    try:
        now = datetime.datetime.now()
        start_time = get_start_time("KRW-BTC")
        end_time = start_time + datetime.timedelta(days=1)
        schedule.run_pending()

        if start_time < now < end_time - datetime.timedelta(seconds=10):
            target_price = get_target_price("KRW-BTC", 0.8)
            current_price = get_current_price("KRW-BTC")
            # print("Target price = {} " .format(target_price))
            # print("Current price = {} " .format(current_price))
            
            if target_price < current_price and current_price < predicted_close_price:
                krw = get_balance("KRW")
                print("Current krw = {} " .format(krw))
                print("*"*50)
                if krw > 5000:
                    buy_result = upbit.buy_market_order("KRW-BTC", krw*0.9995)
                    print("Target price = {} " .format(target_price))
                    print("Current price = {} " .format(current_price))
                    post_message(myToken,"#python", "Target price : " +str(target_price))
                    post_message(myToken,"#python", "Current price : " +str(current_price))
                    post_message(myToken,"#python", "BTC buy : " +str(buy_result))
        else:
            btc = get_balance("BTC")
            if btc > 0.00008:
                sell_result = upbit.sell_market_order("KRW-BTC", btc*0.9995)
                print("Target price = {} " .format(target_price))
                print("Current price = {} " .format(current_price))
                post_message(myToken,"#python", "Target price : " +str(target_price))
                post_message(myToken,"#python", "Current price : " +str(current_price))
                post_message(myToken,"#python", "BTC buy : " +str(sell_result))
        time.sleep(1)
    except Exception as e:
        print(e)
        post_message(myToken,"#python", e)
        time.sleep(1)
