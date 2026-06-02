from panda_backtest.api.api import *
import traceback

TARGET_SYMBOL = '600519.SH'
BUY_SHARES = 1000

def initialize(context):
    SRLogger.info(f"策略初始化: 首日买入 {TARGET_SYMBOL} x{BUY_SHARES}股，持有至结束")
    context.stock_pool = [TARGET_SYMBOL]
    context.first_buy_done = False
    context.entry_price = None


def before_trading(context):
    pass


def handle_data(context, bar_dict):
    if context.first_buy_done:
        return

    stock_account = context.run_info.stock_account

    for symbol in context.stock_pool:
        if symbol not in bar_dict:
            continue
        bar = bar_dict[symbol]
        try:
            order_shares(stock_account, symbol, BUY_SHARES)
            context.first_buy_done = True
            context.entry_price = float(bar.close)
            SRLogger.info(f"[首日买入] date={context.now}, symbol={symbol}, "
                          f"shares={BUY_SHARES}, price={context.entry_price:.2f}")
        except Exception:
            SRLogger.error(f"买入失败: {traceback.format_exc()}")


def after_trading(context):
    account = context.stock_account_dict['8888']
    total_value = account.total_value
    positions = account.positions

    pos_info = ""
    if TARGET_SYMBOL in positions:
        pos = positions[TARGET_SYMBOL]
        pos_info = f", position={pos.quantity}股, market_value={pos.market_value:.2f}"

    SRLogger.info(f"date={context.now}, total_value={total_value:.2f}{pos_info}")
