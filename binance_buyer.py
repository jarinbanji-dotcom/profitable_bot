"""
binance_buyer.py  —  Drop-in replacement for bybit.py
Rename this file to `binance_buyer.py` and in your main scraper replace:
    import bybit  →  import binance_buyer as bybit
Everything else (connect_bybit, function names) stays the same.
"""

import time
import decimal
import threading
from datetime import datetime, timezone

from binance.client import Client
from binance.exceptions import BinanceAPIException

# ── Credentials ──────────────────────────────────────────────────────────────
API_KEY    = "8xTq5KUonQqSn0ml0u69PmcTF0Wg075CCvxdbHIpuwvK2et90PxxXIVxXgYLf32G"
API_SECRET = "9OCWvgKyq8ItD9rsEDggfgBWssV6K4SSNK49WJfxu7GJ4S8Az0rsqox6mXxGzb5m"

client = Client(API_KEY, API_SECRET)

# ── Shared results cache (mirrors your bybit structure) ───────────────────────
results = {}


# ─────────────────────────────────────────────────────────────────────────────
# WARM-UP  (called in your idle loop to keep connection hot)
# ─────────────────────────────────────────────────────────────────────────────
def run_session_continously(symbol):
    """
    Pre-fetches ticker + symbol info in parallel so the data is cached
    and ready the moment a listing fires.
    Called in your idle i==0/i==1/i==2 rotation — keep that as-is.
    """
    def fetch_ticker():
        results['ticker'] = client.get_symbol_ticker(symbol=symbol)

    def fetch_instr():
        results['instr'] = client.get_symbol_info(symbol)

    t1 = threading.Thread(target=fetch_ticker)
    t2 = threading.Thread(target=fetch_instr)
    t1.start(); t2.start()
    t1.join();  t2.join()


# ─────────────────────────────────────────────────────────────────────────────
# BALANCE
# ─────────────────────────────────────────────────────────────────────────────
def get_bal(token):
    """Returns free balance for a token (float)."""
    try:
        bal = client.get_asset_balance(asset=token)
        return float(bal['free']) if bal else 0.0
    except Exception as e:
        print(f"get_bal error: {e}")
        return 0.0


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def _get_symbol_filters(symbol):
    """Returns a dict of filterType → filter dict for a symbol."""
    info = client.get_symbol_info(symbol)
    if not info:
        raise RuntimeError(f"Symbol {symbol} not found on Binance")
    return {f['filterType']: f for f in info['filters']}


def _round_step(value: float, step_str: str) -> float:
    """Floor-rounds value to the step size given as a string like '0.001'."""
    step = decimal.Decimal(step_str)
    val  = decimal.Decimal(str(value))
    return float(val.quantize(step, rounding=decimal.ROUND_DOWN))


def _round_tick(value: float, tick_str: str) -> float:
    """Floor-rounds price to tick size."""
    return _round_step(value, tick_str)


# ─────────────────────────────────────────────────────────────────────────────
# TAKE-PROFIT ORDER
# ─────────────────────────────────────────────────────────────────────────────
def place_tp_order(order_id: str, tp_percent: float, symbol: str):
    """
    Mirrors your Bybit place_tp_order signature exactly.
    Fetches the filled buy order, then places a GTC limit sell at +tp_percent.
    """
    st = time.time()

    # 1. Get fill info
    order = client.get_order(symbol=symbol, orderId=int(order_id))
    avg_buy_price = float(order['cummulativeQuoteQty']) / float(order['executedQty'])
    qty_bought    = float(order['executedQty'])

    # 2. Use full executed qty (no fee deduction — Binance deducts fee from received token automatically)
    actual_qty = qty_bought

    # 3. Get precision rules
    filters   = _get_symbol_filters(symbol)
    tick_size = filters['PRICE_FILTER']['tickSize']
    step_size = filters['LOT_SIZE']['stepSize']
    min_qty   = float(filters['LOT_SIZE']['minQty'])
    max_qty   = float(filters['LOT_SIZE']['maxQty'])

    # 4. TP price
    tp_price_raw = avg_buy_price * (1 + tp_percent)
    tick_dec    = decimal.Decimal(tick_size).normalize()
    final_price = float(decimal.Decimal(str(tp_price_raw)).quantize(tick_dec, rounding=decimal.ROUND_DOWN))

    # Floor qty to step size, then clamp within min/max
    step_dec  = decimal.Decimal(step_size).normalize()
    final_qty = float(decimal.Decimal(str(actual_qty)).quantize(step_dec, rounding=decimal.ROUND_DOWN))
    final_qty = max(min_qty, min(final_qty, max_qty))

    # Clamp price within PRICE_FILTER min/max
    price_min   = float(filters['PRICE_FILTER']['minPrice'])
    price_max_f = float(filters['PRICE_FILTER']['maxPrice'])
    if price_max_f > 0:
        final_price = max(price_min, min(final_price, price_max_f))

    # 5. Place sell
    response = client.order_limit_sell(
        symbol      = symbol,
        quantity    = str(final_qty),
        price       = str(final_price),
        timeInForce = 'GTC'
    )

    print(f"[TP] Sell {final_qty} {symbol} @ {final_price}  |  took {time.time()-st:.3f}s")
    return response


# ─────────────────────────────────────────────────────────────────────────────
# MAIN BUY  —  aggressive, volatility-proof
# ─────────────────────────────────────────────────────────────────────────────
def place_aggressive_spot_buy(symbol: str, usdt_amount: float):
    """
    Strategy (in order of preference):
      1. Market buy with quoteOrderQty  → guaranteed fill, absorbs any spread
      2. If market fails → wide limit at +8% above ask (Binance allows this)
      3. If wide limit rejected → retry at max allowed by PERCENT_PRICE filter

    After fill → place 10% TP limit sell.
    """
    st_total = time.time()
    print(f"[{datetime.now(timezone.utc)}] BUY START  symbol={symbol}  usdt={usdt_amount}")

    # ── Fetch live price + rules ──────────────────────────────────────────────
    def fetch_ticker():
        results['ticker'] = client.get_symbol_ticker(symbol=symbol)
    def fetch_instr():
        results['instr'] = client.get_symbol_info(symbol)

    t1 = threading.Thread(target=fetch_ticker)
    t2 = threading.Thread(target=fetch_instr)
    t1.start(); t2.start()
    t1.join();  t2.join()

    ticker    = results['ticker']
    sym_info  = results['instr']

    last_price = float(ticker['price'])
    filters    = {f['filterType']: f for f in sym_info['filters']}

    tick_size  = filters['PRICE_FILTER']['tickSize']
    step_size  = filters['LOT_SIZE']['stepSize']
    min_qty    = float(filters['LOT_SIZE']['minQty'])
    min_notional = float(filters.get('MIN_NOTIONAL', {}).get('minNotional', 5.0))

    print(f"  last_price={last_price}  tick={tick_size}  step={step_size}")

    # ── ATTEMPT 1: Market order (quoteOrderQty = spend exactly usdt_amount) ──
    order_id = None
    try:
        print(f"[{datetime.now(timezone.utc)}] Trying MARKET order...")
        buy_order = client.order_market_buy(
            symbol        = symbol,
            quoteOrderQty = str(usdt_amount)   # Binance fills this many USDT worth
        )
        order_id = str(buy_order['orderId'])
        print(f"  MARKET filled  orderId={order_id}  status={buy_order['status']}")

    except BinanceAPIException as e:
        print(f"  Market failed: {e.code} {e.message}")

        # ── ATTEMPT 2: Wide limit at +8% ──────────────────────────────────────
        try:
            wide_price = _round_tick(last_price * 1.08, tick_size)
            qty        = _round_step(usdt_amount / wide_price, step_size)

            # Guard: Binance PERCENT_PRICE filter check
            if 'PERCENT_PRICE' in filters:
                pp          = filters['PERCENT_PRICE']
                multiplier  = float(pp['multiplierUp'])          # e.g. 1.05 or 5.0
                avg_price   = float(client.get_avg_price(symbol=symbol)['price'])
                max_allowed = _round_tick(avg_price * multiplier, tick_size)

                if wide_price > max_allowed:
                    print(f"  PERCENT_PRICE cap={max_allowed}, clamping wide_price")
                    wide_price = max_allowed
                    qty        = _round_step(usdt_amount / wide_price, step_size)

            if qty < min_qty or (qty * wide_price) < min_notional:
                raise RuntimeError(f"Qty {qty} below minimums — aborting")

            print(f"[{datetime.now(timezone.utc)}] Trying LIMIT +8%  price={wide_price}  qty={qty}")
            buy_order = client.order_limit_buy(
                symbol      = symbol,
                quantity    = str(qty),
                price       = str(wide_price),
                timeInForce = 'GTC'
            )
            order_id = str(buy_order['orderId'])
            print(f"  LIMIT placed  orderId={order_id}  status={buy_order['status']}")

        except BinanceAPIException as e2:
            print(f"  Wide limit failed: {e2.code} {e2.message}")

            # ── ATTEMPT 3: Retry at max allowed price ─────────────────────────
            if 'PERCENT_PRICE' in filters:
                try:
                    avg_price   = float(client.get_avg_price(symbol=symbol)['price'])
                    max_allowed = _round_tick(
                        avg_price * float(filters['PERCENT_PRICE']['multiplierUp']) * 0.999,
                        tick_size
                    )
                    qty = _round_step(usdt_amount / max_allowed, step_size)
                    print(f"[{datetime.now(timezone.utc)}] Retry at PERCENT_PRICE max={max_allowed}  qty={qty}")
                    buy_order = client.order_limit_buy(
                        symbol      = symbol,
                        quantity    = str(qty),
                        price       = str(max_allowed),
                        timeInForce = 'GTC'
                    )
                    order_id = str(buy_order['orderId'])
                    print(f"  Retry filled  orderId={order_id}")
                except BinanceAPIException as e3:
                    raise RuntimeError(f"All buy attempts failed: {e3.code} {e3.message}")
            else:
                raise RuntimeError(f"Wide limit failed and no PERCENT_PRICE filter: {e2}")

    print(f"  Buy placed in {time.time()-st_total:.3f}s")

    # ── Confirm fill (wait up to 2s) ─────────────────────────────────────────
    token     = symbol.replace('USDT', '')
    time.sleep(0.15)
    token_bal = get_bal(token)
    print(f"  Token balance after buy: {token_bal}")

    if token_bal < min_qty:
        # Cancel unfilled limit and abort
        try:
            client.cancel_order(symbol=symbol, orderId=int(order_id))
            print(f"  Cancelled unfilled order {order_id}")
        except Exception:
            pass
        raise RuntimeError("Order not filled — position not opened")

    # Wait a moment for full fill confirmation before placing TP
    time.sleep(0.85)

    # ── Take Profit ───────────────────────────────────────────────────────────
    tp_percent = 0.10   # 10%
    print(f"[{datetime.now(timezone.utc)}] Placing TP @ +{tp_percent*100:.0f}%")
    tp_response = place_tp_order(order_id, tp_percent, symbol)
    print(f"  TP response: {tp_response}")

    print(f"[{datetime.now(timezone.utc)}] DONE  total={time.time()-st_total:.3f}s")
    return order_id


