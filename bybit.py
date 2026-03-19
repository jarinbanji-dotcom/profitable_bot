from datetime import datetime, timezone
import time
import re
import threading

from pybit.unified_trading import HTTP


# 1. Initialize the session
# Use testnet=True for demo trading; set to False for real trading
session = HTTP(
    testnet=False,
    api_key="nrk5LoL4OsGXVetTgZ",
    api_secret="F9YtDDwUeAAgTzhAKwAl3h1u7XoqAKAMx6bP"
)

import math

# Results container
results = {}

def run_session_continously(symbol):
    st = time.time()
    print(f"[{datetime.now(timezone.utc)}] inside fetch ticker and fetch instr")

    

    # ── Fetch both in parallel using threads ──
    def fetch_ticker():
        results['ticker'] = session.get_tickers(category="spot", symbol=symbol)

    def fetch_instr():
        results['instr'] = session.get_instruments_info(category="spot", symbol=symbol)

    t1 = threading.Thread(target=fetch_ticker)
    t2 = threading.Thread(target=fetch_instr)

    t1.start()
    t2.start()
    t1.join()
    t2.join()




def place_tp_order(order_id, tp_percent, symbol):
    st = time.time()

    # 1. Fetch Order History
    order_history = session.get_order_history(category="spot", orderId=order_id)
    fill_info = order_history['result']['list'][0]

    avg_buy_price = float(fill_info['avgPrice'])
    qty_bought = float(fill_info['cumExecQty'])

    # Use 0.999 (0.1% fee) instead of 0.98 to keep more profit
    actual_qty = qty_bought * 0.98


    # 2. Fetch Symbol Rules (Precision)
    instr = session.get_instruments_info(category="spot", symbol=symbol)
    price_filter = instr['result']['list'][0]['priceFilter']
    lot_filter = instr['result']['list'][0]['lotSizeFilter']

    # Get required decimal places
    # Bybit often provides 'tickSize' (e.g., "0.0001")
    price_tick = price_filter['tickSize']
    qty_step = lot_filter['basePrecision']  # e.g., "0.000001"

    # 3. Calculate TP Price
    tp_price_raw = avg_buy_price * (1 + tp_percent)

    # 4. Format numbers correctly based on Bybit's rules
    # This replaces hardcoded round(x, 2)
    def format_step(value, step):
        precision = len(step.split('.')[-1]) if '.' in step else 0
        return "{:0.{}f}".format(value, precision)

    final_qty = format_step(actual_qty, qty_step)
    final_price = format_step(tp_price_raw, price_tick)


    # 5. Place Order

    response = session.place_order(
        category="spot",
        symbol=symbol,
        side="Sell",
        orderType="Limit",
        qty=final_qty,
        price=final_price,
        timeInForce="GTC"
    )
    print(f"Sold {final_qty} {symbol} at {final_price}")
    print("Take profit time:", time.time() - st)

    print(f"[{datetime.now(timezone.utc)}] after take profit time")

    
    return response



#place_tp_order("2150087400385420288",0.05,"USDCUSDT")


#Buy order response: {'retCode': 0, 'retMsg': 'OK', 'result': {'orderId': '2150087400385420288', 'orderLinkId': '2150087400385420289'}, 'retExtInfo': {}, 'time': 1771046391472}
# Buy order response: {'retCode': 0, 'retMsg': 'OK', 'result': {'orderId': '2154568860798557184', 'orderLinkId': '2154568860798557185'}, 'retExtInfo': {}, 'time': 1771580623185}









#place_buy_order("USDCUSDT", buy_qty=7)

#place_tp_order("2153135979010202624",0.05,"USDCUSDT")











# Usage


import decimal


def get_bal(token):
    res = session.get_wallet_balance(accountType="UNIFIED", coin=token)
    return float(res['result']['list'][0]['coin'][0]['walletBalance'])


def get_new_price(e):
    error_msg = str(e)

    # Check if the error is 170193 (Price Limit Protection)
    if "170193" in error_msg:
        print(f"[{datetime.now(timezone.utc)}] inside error message time")
        print(f"Caught Limit Error: {error_msg}")

        # Use regex to find the price in the error string (e.g., "0.1643")
        # Pattern looks for digits followed by a dot and more digits
        found_prices = re.findall(r"\d+\.\d+", error_msg)
        print("found prices: ", found_prices)

        if found_prices:
            # The exchange limit is usually the first number found
            exchange_limit = float(found_prices[0])
            print("exchange limit :", exchange_limit)

            # Deduct a tiny "Safety Buffer" (e.g., 0.01% or 1 tick)
            # For SKR/CFG, using 0.9998 ensures you are safely inside the cap
            retry_price = round(exchange_limit * 0.9998, 6)

            return retry_price
        else:
            return None
    


def place_aggressive_spot_buy(symbol, usdt_amount):
    # 1. Get Market Price & Instrument Rules

    st=time.time()

    run_session_continously(symbol)

    
    
    ticker = results['ticker']
    en1=time.time()
    print("ticker time : ",en1-st)

    instr = results['instr']
    en2=time.time()
    print("instr :",en2-en1)

    last_price = float(ticker['result']['list'][0]['usdIndexPrice'])
    print(last_price)
    rules = instr['result']['list'][0]

    # 2. Get the Dynamic Limit (RatioX)
    # If RatioX is 0.05, we use 0.04 for safety
    ratio_x = float(rules['riskParameters']['priceLimitRatioX'])
    if(ratio_x>0.05):
        ratio_x=0.05
    print("x ratio : ",ratio_x)
    safe_ratio = ratio_x*1.2
    print("safe_ratio : ",safe_ratio)

    # 3. Calculate Target Price (Market + 4%)
    target_price = last_price * (1 + safe_ratio)
    target_price=round(target_price * 0.9998, 6)
    print("target price : ",target_price)

    # 4. Critical: Round to Tick Size (0.000001)
    tick = decimal.Decimal(rules['priceFilter']['tickSize'])
    final_buy_price = float(decimal.Decimal(str(target_price)).quantize(tick, rounding=decimal.ROUND_DOWN))

    print("final buy price : ",final_buy_price)

    # 5. Calculate Quantity & Round to Base Precision (e.g., 0.1)
    base_precision = rules['lotSizeFilter']['basePrecision']
    qty = float(decimal.Decimal(str(usdt_amount / final_buy_price)).quantize(decimal.Decimal(base_precision),
                                                                             rounding=decimal.ROUND_DOWN))

    print("qty :",qty)

    print(f"Sending Limit Buy: {qty} @ {final_buy_price} (Buffer: {safe_ratio * 100}%)")

    # 6. Execute with IOC (Immediate or Cancel)

    st=time.time()
    try:
        buy_order=session.place_order(
            category="spot",
            symbol=symbol,
            side="Buy",
            orderType="Limit",
            qty=str(qty),
            price=str(final_buy_price),
            timeInForce="GTC"
        )
    except Exception as e:
        print("inside exeption")
        new_price=get_new_price(e)
        if(new_price):
            final_buy_price = float(decimal.Decimal(str(new_price)).quantize(tick, rounding=decimal.ROUND_DOWN))
            print("final buy price : ",final_buy_price)
            qty = float(decimal.Decimal(str(usdt_amount / final_buy_price)).quantize(decimal.Decimal(base_precision),rounding=decimal.ROUND_DOWN))
            print(f"new Sending Limit Buy: {qty} @ {final_buy_price} (Buffer: {safe_ratio * 100}%)")
            buy_order=session.place_order(category="spot",symbol=symbol,side="Buy",orderType="Limit",qty=str(qty),price=str(final_buy_price),timeInForce="IOC")
    print(f"[{datetime.now(timezone.utc)}] after buy order time")
            
            
        
        

    en=time.time()
    print("buy order time : ",en-st)
    orderid=buy_order["result"]["orderId"]
    print("buy order id : ",orderid)
    tp_percent = 0.1 # 10%

    st=time.time()
    token=symbol[:-4]
    print(token)
    time.sleep(0.1)
    token_bal = get_bal(token)
    print(token_bal)
    
    if(token_bal<0.01):
        response = session.cancel_order(
            category="spot",
            symbol=symbol,
            orderId=orderid
        )
        raise RuntimeError("Order failed")
    en=time.time()
    print(en-st)

    time.sleep(0.9)



    print(place_tp_order(orderid,tp_percent,symbol))




st=time.time()
#print(place_aggressive_spot_buy("USDCUSDT",8))
en=time.time()
print("time taken :",en-st)


"""
#2154426114288917504


order_details = session.get_order_history(
    category="spot",
    orderId="2154426114288917504"
)

print(order_details)

# Extracting the reason
if order_details['result']['list']:
    order_info = order_details['result']['list'][0]
    print(f"Status: {order_info['orderStatus']}")
    print(f"Reject Reason: {order_info['rejectReason']}")
    print(f"Cancel Type: {order_info['cancelType']}")



# Fetch the last 5 orders for a specific symbol
history = session.get_order_history(
    category="spot",
    symbol="AZTECUSDT",
    limit=10
)

print(history)

# Loop through to find IDs and their statuses
for order in history['result']['list']:
    print(f"ID: {order['orderId']} | Status: {order['orderStatus']} | Side: {order['side']}")


print("order history : ", order_history)
print("fill infor : ", fill_info)
print("avg buy price ", avg_buy_price)
print("qunty bought : ", qty_bought)
print("actual bought : ", actual_qty)
print("instr : ", instr)
print("price filter : ", price_filter)
print("lot filter : ", lot_filter)
print("step size : ", price_tick)
print("qty step", qty_step)
print("tp price : ", tp_price_raw)
"""


















