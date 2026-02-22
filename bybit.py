from datetime import datetime, timezone
import time

from pybit.unified_trading import HTTP


# 1. Initialize the session
# Use testnet=True for demo trading; set to False for real trading
session = HTTP(
    testnet=False,
    api_key="nrk5LoL4OsGXVetTgZ",
    api_secret="F9YtDDwUeAAgTzhAKwAl3h1u7XoqAKAMx6bP"
)

import math



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

    
    return response



#place_tp_order("2150087400385420288",0.05,"USDCUSDT")


#Buy order response: {'retCode': 0, 'retMsg': 'OK', 'result': {'orderId': '2150087400385420288', 'orderLinkId': '2150087400385420289'}, 'retExtInfo': {}, 'time': 1771046391472}
# Buy order response: {'retCode': 0, 'retMsg': 'OK', 'result': {'orderId': '2154568860798557184', 'orderLinkId': '2154568860798557185'}, 'retExtInfo': {}, 'time': 1771580623185}




def place_buy_order(symbol, buy_qty):

    st=time.time()
    """
    Place a spot market buy and a take-profit limit sell based on a percentage
    """
    # --- 1. Market Buy Order ---
    print("Placing Spot Market Buy...")
    buy_order = session.place_order(
        category="spot",
        symbol=symbol,
        side="Buy",
        orderType="Market",
        qty=str(buy_qty)  # amount in quote currency, e.g., USDT
    )
    print("Buy order response:", buy_order)

    en=time.time()
    print("Buy order time : ",en-st)
    now_utc = datetime.now(timezone.utc)

    print("Buy order time :",now_utc)

    orderid=buy_order["result"]["orderId"]
    tp_percent = 0.05 # 5%

    time.sleep(1)


    print(place_tp_order(orderid,tp_percent,symbol))




#place_buy_order("USDCUSDT", buy_qty=7)

#place_tp_order("2153135979010202624",0.05,"USDCUSDT")









def buy_with_3_percent_buffer(symbol):
    # 1. Fetch current price via REST (Fastest for one-time use)
    ticker = session.get_tickers(category="spot", symbol=symbol)

    if ticker['retCode'] == 0 and ticker['result']['list']:
        last_price = float(ticker['result']['list'][0]['lastPrice'])
        print(last_price)
        """
        # 2. Add 3% buffer for the Limit Order
        limit_price = round(last_price * 1.03, 6)

        print(f"Market: {last_price} | Placing Limit Buy at: {limit_price}")

        # 3. Place the order
        return session.place_order(
            category="spot",
            symbol=symbol,
            side="Buy",
            orderType="Limit",
            qty=qty,
            price=str(limit_price),
            timeInForce="IOC"  # Immediate or Cancel (best for 'aggressive' entries)
        )
        """
    return "Error fetching price"


# Usage


import decimal





def place_aggressive_spot_buy(symbol, usdt_amount):
    # 1. Get Market Price & Instrument Rules
    st=time.time()
    ticker = session.get_tickers(category="spot", symbol=symbol)
    en1=time.time()
    print("ticker time : ",en1-st)

    instr = session.get_instruments_info(category="spot", symbol=symbol)
    en2=time.time()
    print("instr :",en2-en1)

    last_price = float(ticker['result']['list'][0]['lastPrice'])
    print(last_price)
    rules = instr['result']['list'][0]

    # 2. Get the Dynamic Limit (RatioX)
    # If RatioX is 0.05, we use 0.04 for safety
    ratio_x = float(rules['riskParameters']['priceLimitRatioX'])
    print("x ratio : ",ratio_x)
    safe_ratio = ratio_x - 0.01
    print("safe_ratio : ",safe_ratio)

    # 3. Calculate Target Price (Market + 4%)
    target_price = last_price * (1 + safe_ratio)
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
    """
    return session.place_order(
        category="spot",
        symbol=symbol,
        side="Buy",
        orderType="Limit",
        qty=str(qty),
        price=str(final_buy_price),
        timeInForce="IOC"
    )
    """

st=time.time()
place_aggressive_spot_buy("AZTECUSDT",8)
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
