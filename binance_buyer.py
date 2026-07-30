"""
binance_buyer.py  —  Drop-in replacement for bybit.py
Change in your main scraper:
    import bybit  →  import binance_buyer as bybit
"""

import time
import decimal
import threading
from datetime import datetime, timezone

from binance.client import Client
from binance.exceptions import BinanceAPIException

# ── Credentials ───────────────────────────────────────────────────────────────
API_KEY    = "YOUR_BINANCE_API_KEY"
API_SECRET = "YOUR_BINANCE_API_SECRET"

client = Client(API_KEY, API_SECRET)

# ── Shared cache ──────────────────────────────────────────────────────────────
results = {}


# ─────────────────────────────────────────────────────────────────────────────
# WARM-UP  (called in idle loop to keep connection hot)
# ─────────────────────────────────────────────────────────────────────────────
def run_session_continously(symbol):
    """Pre-fetches symbol filters so they're cached for the limit fallback path."""
    def fetch_instr():
        results['instr'] = client.get_symbol_info(symbol)
    t = threading.Thread(target=fetch_instr)
    t.start(); t.join()


# ─────────────────────────────────────────────────────────────────────────────
# BALANCE
# ─────────────────────────────────────────────────────────────────────────────
def get_bal(token):
    try:
        bal = client.get_asset_balance(asset=token)
        return float(bal['free']) if bal else 0.0
    except Exception as e:
        print(f"get_bal error: {e}")
        return 0.0


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def _get_filters(symbol):
    info = client.get_symbol_info(symbol)
    if not info:
        raise RuntimeError(f"Symbol {symbol} not found on Binance")
    return {f['filterType']: f for f in info['filters']}


def _floor(value: float, step_str: str) -> float:
    step = decimal.Decimal(step_str).normalize()
    return float(decimal.Decimal(str(value)).quantize(step, rounding=decimal.ROUND_DOWN))


# ─────────────────────────────────────────────────────────────────────────────
# TAKE-PROFIT  — filters passed in, no extra API call
# ─────────────────────────────────────────────────────────────────────────────
def place_tp_order(order_id: str, tp_percent: float, symbol: str, filters: dict = None):
    st = time.time()

    # 1. Get fill info + filters in parallel
    order_result = {}
    filter_result = {}

    def fetch_order():
        order_result['o'] = client.get_order(symbol=symbol, orderId=int(order_id))

    def fetch_filters():
        filter_result['f'] = filters if filters else _get_filters(symbol)

    t1 = threading.Thread(target=fetch_order)
    t2 = threading.Thread(target=fetch_filters)
    t1.start(); t2.start()
    t1.join();  t2.join()

    order     = order_result['o']
    f         = filter_result['f']

    avg_price = float(order['cummulativeQuoteQty']) / float(order['executedQty'])
    qty_bought = float(order['executedQty'])

    tick_size = f['PRICE_FILTER']['tickSize']
    step_size = f['LOT_SIZE']['stepSize']
    min_qty   = float(f['LOT_SIZE']['minQty'])
    max_qty   = float(f['LOT_SIZE']['maxQty'])
    price_min = float(f['PRICE_FILTER']['minPrice'])
    price_max = float(f['PRICE_FILTER']['maxPrice'])

    # 2. Calculate TP price + qty
    tp_price  = avg_price * (1 + tp_percent)
    final_price = _floor(tp_price, tick_size)
    if price_max > 0:
        final_price = max(price_min, min(final_price, price_max))

    final_qty = _floor(qty_bought, step_size)
    final_qty = max(min_qty, min(final_qty, max_qty))

    # 3. Place sell
    response = client.order_limit_sell(
        symbol      = symbol,
        quantity    = str(final_qty),
        price       = str(final_price),
        timeInForce = 'GTC'
    )

    print(f"[TP] Sell {final_qty} {symbol} @ {final_price}  |  took {time.time()-st:.3f}s")
    return response


# ─────────────────────────────────────────────────────────────────────────────
# MAIN BUY  —  market order fires immediately, no pre-fetch needed
# ─────────────────────────────────────────────────────────────────────────────
def place_aggressive_spot_buy(symbol: str, usdt_amount: float):
    st_total = time.time()
    print(f"[{datetime.now(timezone.utc)}] BUY START  symbol={symbol}  usdt={usdt_amount}")

    filters   = None
    order_id  = None
    buy_order = None

    # ── ATTEMPT 1: Market order — fires immediately, no pre-fetch ────────────
    try:
        print(f"[{datetime.now(timezone.utc)}] Trying MARKET order...")
        buy_order = client.order_market_buy(
            symbol        = symbol,
            quoteOrderQty = str(usdt_amount)
        )
        order_id = str(buy_order['orderId'])
        print(f"  MARKET filled  orderId={order_id}  status={buy_order['status']}")

    except BinanceAPIException as e:
        print(f"  Market failed: {e.code} {e.message}")

        # Need filters for limit fallback — fetch now
        filters = _get_filters(symbol)
        tick_size = filters['PRICE_FILTER']['tickSize']
        step_size = filters['LOT_SIZE']['stepSize']
        min_qty   = float(filters['LOT_SIZE']['minQty'])
        min_notional = float(filters.get('MIN_NOTIONAL', {}).get('minNotional', 5.0))

        # Get current price for limit calculation
        ticker     = client.get_symbol_ticker(symbol=symbol)
        last_price = float(ticker['price'])

        # ── ATTEMPT 2: Wide limit at +8% ──────────────────────────────────────
        try:
            wide_price = _floor(last_price * 1.08, tick_size)
            qty        = _floor(usdt_amount / wide_price, step_size)

            if 'PERCENT_PRICE' in filters:
                avg_price   = float(client.get_avg_price(symbol=symbol)['price'])
                max_allowed = _floor(avg_price * float(filters['PERCENT_PRICE']['multiplierUp']), tick_size)
                if wide_price > max_allowed:
                    wide_price = max_allowed
                    qty        = _floor(usdt_amount / wide_price, step_size)

            if qty < min_qty or (qty * wide_price) < min_notional:
                raise RuntimeError(f"Qty {qty} below minimums")

            print(f"[{datetime.now(timezone.utc)}] Trying LIMIT +8%  price={wide_price}  qty={qty}")
            buy_order = client.order_limit_buy(
                symbol=symbol, quantity=str(qty), price=str(wide_price), timeInForce='GTC'
            )
            order_id = str(buy_order['orderId'])
            print(f"  LIMIT placed  orderId={order_id}  status={buy_order['status']}")

        except BinanceAPIException as e2:
            print(f"  Wide limit failed: {e2.code} {e2.message}")

            # ── ATTEMPT 3: Clamp to PERCENT_PRICE max ─────────────────────────
            if 'PERCENT_PRICE' in filters:
                avg_price   = float(client.get_avg_price(symbol=symbol)['price'])
                max_allowed = _floor(
                    avg_price * float(filters['PERCENT_PRICE']['multiplierUp']) * 0.999,
                    tick_size
                )
                qty = _floor(usdt_amount / max_allowed, step_size)
                print(f"[{datetime.now(timezone.utc)}] Retry PERCENT_PRICE max={max_allowed}  qty={qty}")
                buy_order = client.order_limit_buy(
                    symbol=symbol, quantity=str(qty), price=str(max_allowed), timeInForce='GTC'
                )
                order_id = str(buy_order['orderId'])
                print(f"  Retry placed  orderId={order_id}")
            else:
                raise RuntimeError(f"All buy attempts failed: {e2}")

    print(f"  Buy placed in {time.time()-st_total:.3f}s")

    # ── Confirm fill ──────────────────────────────────────────────────────────
    token = symbol.replace('USDT', '')
    time.sleep(0.15)
    token_bal = get_bal(token)
    print(f"  Token balance after buy: {token_bal}")

    min_qty_check = float(filters['LOT_SIZE']['minQty']) if filters else 0.0001
    if token_bal < min_qty_check:
        try:
            client.cancel_order(symbol=symbol, orderId=int(order_id))
            print(f"  Cancelled unfilled order {order_id}")
        except Exception:
            pass
        raise RuntimeError("Order not filled — position not opened")

    time.sleep(0.85)

    # ── Take Profit ───────────────────────────────────────────────────────────
    tp_percent = 0.10
    print(f"[{datetime.now(timezone.utc)}] Placing TP @ +{tp_percent*100:.0f}%")
    tp_response = place_tp_order(order_id, tp_percent, symbol, filters)
    print(f"  TP response: {tp_response}")

    print(f"[{datetime.now(timezone.utc)}] DONE  total={time.time()-st_total:.3f}s")
    return order_id
