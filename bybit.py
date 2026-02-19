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




def wait_order():
    time.sleep(0.8)
    print("wait ra")

def place_tp_order(order_id,tp_percent,symbol):
    st = time.time()

    order_history = session.get_order_history(category="spot", orderId=order_id)
    print(order_history)
    fill_info = order_history['result']['list'][0]

    avg_buy_price = float(fill_info['avgPrice'])
    qty_bought = float(fill_info['cumExecQty'])
    print(qty_bought)
    print(avg_buy_price)

    qty_bought=0.98*qty_bought
    print(qty_bought)

    # --- STEP 2: Calculate Percentage TP ---

    tp_price = avg_buy_price * (1 + tp_percent)
    print(tp_price)

    print(str(round(tp_price, 2)))

    session.place_order(
        category="spot",
        symbol=symbol,
        side="Sell",
        orderType="Limit",
        qty=str(round(qty_bought, 2)),
        price=str(round(tp_price, 4)) # Round to match symbol's tick size
    )

    en=time.time()

    print("Take profit time : ",en-st)

    now_utc = datetime.now(timezone.utc)

    print("Sell order time :", now_utc)





#Buy order response: {'retCode': 0, 'retMsg': 'OK', 'result': {'orderId': '2150087400385420288', 'orderLinkId': '2150087400385420289'}, 'retExtInfo': {}, 'time': 1771046391472}





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


    place_tp_order(orderid,tp_percent,symbol)




place_buy_order("USDCUSDT", buy_qty=7)

#place_tp_order("2153135979010202624",0.05,"USDCUSDT")