#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
from panda_backtest.api.api import *
import pandas as pd
import numpy as np
import talib
import datetime
import panda_data
from panda_factor.generate.macro_factor import MacroFactor


class IndexConstituentsMapper:
    """指数成分股映射器，支持缓存和快速查询"""

    def __init__(self):
        self._constituents_cache = {}  # 缓存不同指数的成分股
        self._last_update = {}  # 记录最后更新时间

    def get_constituents(self, index_code, force_refresh=False):
        """获取指数成分股，带缓存机制"""
        current_date = datetime.datetime.now().strftime('%Y%m%d')

        # 检查是否需要更新缓存
        if not force_refresh and index_code in self._constituents_cache:
            last_update = self._last_update.get(index_code, '')
            if last_update == current_date:
                SRLogger.info(f"使用缓存的 {index_code} 指数成分股数据")
                return self._constituents_cache[index_code]

        # 从数据源获取最新成分股
        constituents = self._fetch_constituents(index_code)

        # 更新缓存
        self._constituents_cache[index_code] = constituents
        self._last_update[index_code] = current_date

        SRLogger.info(f"更新 {index_code} 指数成分股缓存，获取到 {len(constituents)} 只股票")
        return constituents

    def _fetch_constituents(self, index_code):
        """从数据源获取成分股"""
        try:
            # 使用panda_data获取最近一个月的数据来提取成分股
            end_date = datetime.datetime.now().strftime('%Y%m%d')
            start_date = (datetime.datetime.now() - datetime.timedelta(days=30)).strftime('%Y%m%d')

            market_df = panda_data.get_market_data(
                start_date=start_date,
                end_date=end_date,
                indicator=index_code
            )

            if not market_df.empty:
                return market_df['symbol'].unique().tolist()
            else:
                SRLogger.warning(f"无法获取 {index_code} 指数成分股数据")
                return []

        except Exception as e:
            SRLogger.error(f"获取 {index_code} 成分股失败: {str(e)}")
            return []


class StockPoolManager:
    """股票池管理器"""

    def __init__(self):
        self.index_mapper = IndexConstituentsMapper()

    def get_stock_pool(self, pool_type='index', **kwargs):
        """获取不同类型的股票池"""
        if pool_type == 'index':
            index_code = kwargs.get('index_code', '000300')
            return self.index_mapper.get_constituents(index_code)
        elif pool_type == 'all_stocks':
            return panda_data.get_all_symbols()
        elif pool_type == 'custom':
            return kwargs.get('symbols', [])
        else:
            raise ValueError(f"不支持的股票池类型: {pool_type}")


def initialize(context):
    """策略初始化"""
    SRLogger.info("=== 突破策略初始化（全市场多股票版） ===")

    panda_data.init()
    context.macro_factor = MacroFactor()
    # ========== 基础配置 ==========
    context.account = '8888'

    # ========== 策略参数 ==========
    context.max_positions = 10  # 最大持仓股票数量
    context.last_strategy_execution_date = None  # 上次执行策略的日期
    context.previous_date = None
    # ========== 股票池配置 ==========
    # 创建股票池管理器
    pool_manager = StockPoolManager()

    # 获取沪深300指数成分股作为股票池
    try:
        context.stock_pool = pool_manager.get_stock_pool(index_code='000300')

        # 如果获取失败或为空，使用默认测试股票池
        if not context.stock_pool:
            SRLogger.warning("无法获取沪深300成分股，使用默认测试股票池")
            context.stock_pool = ['002317.SZ']

    except Exception as e:
        SRLogger.error(f"获取股票池失败: {str(e)}，使用默认测试股票池")
        context.stock_pool = ['002317.SZ']

    SRLogger.info(f"股票池初始化完成，共 {len(context.stock_pool)} 只股票")


def get_current_position_size(context, stock_id):
    """获取当前持仓数量"""
    try:
        account = context.stock_account_dict.get(context.account)
        if account and hasattr(account, 'positions'):
            position = account.positions.get(stock_id)
            if position and hasattr(position, 'quantity'):
                return position.quantity
            if hasattr(account, 'position_dict'):
                position = account.position_dict.get(stock_id)
                if position:
                    return position.today_amount + position.enable_amount
        return 0
    except Exception as e:
        return 0


def get_current_positions_count(context):
    """获取当前持仓股票数量"""
    try:
        account = context.stock_account_dict.get(context.account)
        if account and hasattr(account, 'positions'):
            return len([p for p in account.positions.values() if p.quantity > 0])
        return 0
    except Exception as e:
        return 0


def calculate_position_size(context, stock_id, price):
    """计算买入股数（基于账户总资产的1%）"""
    try:
        account = context.stock_account_dict.get(context.account)
        if not account:
            return 0

        # 计算目标仓位金额（总资产的1%）
        target_value = account.total_value * context.position_ratio

        # 计算可买入股数（向下取整到100的倍数）
        shares = int(target_value / price / 100) * 100

        return shares
    except Exception as e:
        SRLogger.error(f"计算仓位失败: {str(e)}")
        return 0


def execute_buy(context, state, price):
    """执行买入操作"""
    try:
        # 检查持仓数量限制
        current_positions = get_current_positions_count(context)
        if current_positions >= context.max_positions:
            SRLogger.info(f'[{state.stock_id}] 已达到最大持仓数量 {context.max_positions}，不再买入')
            return

        # 计算买入股数
        shares = calculate_position_size(context, state.stock_id, price)
        if shares <= 0:
            SRLogger.warning(f'[{state.stock_id}] 计算仓位为0，取消买入')
            return

        # 下单
        order_shares(context.account, state.stock_id, shares)

        state.entry_price = price
        state.position_held = True

        # 关闭所有窗口期
        state.in_sar_window = False
        state.window_start_date = None
        state.window_days_count = 0
        state.breakthrough_candidates.clear()

        state.in_surge_window = False
        state.surge_window_start_date = None
        state.surge_window_days_count = 0

        surge_from_sar = 0
        if state.sar_trigger_price:
            surge_from_sar = (price - state.sar_trigger_price) / state.sar_trigger_price * 100

        state.buy_trigger_price = state.sar_trigger_price if state.sar_trigger_price else price
        state.max_profit_price = price

        # 记录交易
        trade_record = {
            'date': context.now,
            'stock_id': state.stock_id,
            'type': '买入',
            'price': price,
            'size': shares,
            'support': state.current_support,
            'resistance': state.current_resistance,
            'sar': state.current_sar,
            'sar_trigger_price': state.sar_trigger_price,
            'surge_from_sar': surge_from_sar
        }
        context.trade_records.append(trade_record)

        SRLogger.info(f'📈 [{state.stock_id}] 三阶段买入完成: 价格={price:.2f}, 数量={shares}, '
                      f'仓位比例={context.position_ratio * 100}%, 相对SAR基准涨幅: {surge_from_sar:.2f}%')

        state.sar_trigger_price = None
    except Exception as e:
        SRLogger.error(f"[{state.stock_id}] 买入执行失败: {str(e)}")


def execute_sell(context, state, price, reason):
    """执行卖出操作"""
    try:
        current_position = get_current_position_size(context, state.stock_id)
        if current_position > 0:
            order_shares(context.account, state.stock_id, -current_position)

        profit_ratio = 0
        if state.entry_price:
            profit_ratio = (price - state.entry_price) / state.entry_price * 100

        state.entry_price = None
        state.position_held = False
        state.buy_trigger_price = None
        state.max_profit_price = None

        # 记录交易
        trade_record = {
            'date': context.now,
            'stock_id': state.stock_id,
            'type': '卖出',
            'price': price,
            'size': current_position,
            'reason': reason,
            'profit_ratio': profit_ratio,
            'sar': state.current_sar
        }
        context.trade_records.append(trade_record)

        SRLogger.info(
            f'📉 [{state.stock_id}] 卖出执行: {reason}, 价格={price:.2f}, 数量={current_position}, 收益率={profit_ratio:.2f}%')
    except Exception as e:
        SRLogger.error(f"[{state.stock_id}] 卖出执行失败: {str(e)}")


def should_execute_strategy_today(context, current_date):
    """判断今天是否应该执行策略（每周第一个交易日）"""
    try:
        # 获取当前是星期几 (0=周一, 1=周二, ..., 6=周日)
        current_dt = datetime.datetime.strptime(current_date, '%Y%m%d')
        if current_dt.weekday() == 0:
            return True

        # 如果是第一次执行，执行策略
        if context.last_strategy_execution_date is None:
            return True

        # 计算当前日期和上次执行日期的天数差
        last_dt = datetime.datetime.strptime(context.last_strategy_execution_date, '%Y%m%d')
        days_diff = (current_dt - last_dt).days

        # 如果相差4天以上（考虑到周末和节假日），认为是新的一周，应该执行
        if days_diff >= 4:
            return True

        return False
    except Exception as e:
        SRLogger.error(f"判断执行日期失败: {str(e)}")
        # 出错时保守起见，执行策略
        return True


def handle_data(context, bar_dict):
    """每个Bar的处理逻辑"""
    current_date = context.now

    # 判断今天是否应该执行策略（每周第一个交易日）
    if not should_execute_strategy_today(context, current_date):
        SRLogger.info(f"[{current_date}] 非每周第一个交易日，跳过策略执行")
        return

    # 更新上次执行日期
    context.last_strategy_execution_date = current_date
    SRLogger.info(f"[{current_date}] 每周第一个交易日，开始执行策略")

    # 从股票池中过滤出有数据的股票
    # 使用 'stock_id in bar_dict' 来判断该股票是否有当前bar数据
    available_stocks = [stock_id for stock_id in context.stock_pool if stock_id in bar_dict]

    # 记录观察到的股票
    for stock_id in available_stocks:
        context.observed_stocks.add(stock_id)

    # 遍历所有可用股票
    for stock_id in available_stocks:
        try:
            # 获取股票状态
            state = get_or_create_stock_state(context, stock_id)

            # ========== 获取当前行情数据 ==========
            bar = bar_dict[stock_id]
            current_high = float(bar.high)
            current_low = float(bar.low)
            current_close = float(bar.close)
            current_volume = float(bar.volume)

            # 数据有效性检查
            if current_close <= 0 or current_volume <= 0:
                continue

            # ========== 更新价格历史 ==========
            current_bar = {
                'date': current_date,
                'high': current_high,
                'low': current_low,
                'close': current_close,
                'volume': current_volume
            }
            state.price_history.append(current_bar)

            # 保持历史数据长度在100个bar以内
            if len(state.price_history) > 100:
                state.price_history.pop(0)

            # ========== 计算技术指标 ==========
            state.current_sar = calculate_sar(state)

            if state.current_sar is not None:
                update_sar_position(state, current_close)

            state.current_support, state.current_resistance = identify_support_resistance(context, state)

            update_breakthrough_window(context, state)
            update_surge_window(context, state)

            # ========== 交易逻辑 ==========
            actual_position = get_current_position_size(context, stock_id)

            # 如果没有持仓，寻找买入机会
            if not state.position_held or actual_position == 0:
                # 第一阶段：检查基础突破条件
                if not state.in_sar_window and not state.in_surge_window:
                    if check_basic_breakthrough(context, state, current_close, current_volume):
                        add_breakthrough_candidate(context, state, current_close, current_volume, current_date)

                # 第二阶段：检查SAR转向信号
                elif state.in_sar_window and is_sar_turn_signal(context, state):
                    start_surge_window(context, state, current_close, current_date)

                # 第三阶段：检查涨幅是否达标
                elif state.in_surge_window and check_price_surge(context, state, current_close):
                    execute_buy(context, state, current_close)

            # 如果有持仓，检查卖出条件
            else:
                if state.entry_price is None:
                    continue

                # 更新最高价
                if state.max_profit_price is None:
                    state.max_profit_price = current_close
                else:
                    state.max_profit_price = max(state.max_profit_price, current_close)

                return_ratio = (current_close - state.entry_price) / state.entry_price * 100

                sell_reason = None

                # 卖出条件1：跌破基准价
                if state.buy_trigger_price and current_close < state.buy_trigger_price:
                    sell_reason = f"跌破基准价 (当前价={current_close:.2f}, 基准价={state.buy_trigger_price:.2f})"

                # 卖出条件2：止盈
                elif return_ratio >= context.take_profit_percent:
                    sell_reason = f"止盈 (收益率={return_ratio:.2f}%)"

                # 卖出条件3：盈利后回撤10%
                elif return_ratio > 0 and state.max_profit_price:
                    drawdown_from_peak = (state.max_profit_price - current_close) / state.max_profit_price * 100
                    if drawdown_from_peak >= context.max_drawdown_percent:
                        sell_reason = f"盈利回撤 (回撤={drawdown_from_peak:.2f}%)"

                if sell_reason:
                    execute_sell(context, state, current_close, sell_reason)

        except Exception as e:
            SRLogger.error(f"处理股票 {stock_id} 时发生错误: {str(e)}")
            continue


def before_trading(context):
    """盘前处理"""
    try:
        account = context.stock_account_dict[context.account]
        positions_count = get_current_positions_count(context)

        # 统计窗口期股票数量
        stage1_count = sum(1 for s in context.stock_states.values() if s.in_sar_window)
        stage2_count = sum(1 for s in context.stock_states.values() if s.in_surge_window)

        SRLogger.info(f"[{context.now}] 开盘前 - 账户总资产：{account.total_value:.2f}, "
                      f"可用资金：{account.cash:.2f}, 持仓股票数：{positions_count}/{context.max_positions}")

        check_out_list = get_stock_list(context)

    except Exception as e:
        SRLogger.error(f"盘前处理失败: {str(e)}")


def filter_kcb_stock(stock_list):

    return [stock for stock in stock_list if not str.startswith('688')]

def cal_roec(context):

    financial_formulas = [
        "4 * QROE - REF(QROE, 1) - REF(QROE, 2) - REF(QROE, 3) - REF(QROE, 4)",
        "total_liab / total_assets",
    ]

    df = context.macro_factor.create_factor_from_formula_pro(
        factor_logger=logger,
        formulas=financial_formulas,
        symbols=['600519.SH'],
        start_date="20240101",
        end_date="20251111"
    )
    df.columns = ['roec', 'ratio']
    df = df.sort_values(by='ratio')
    df = df[df['ratio'] < df['ratio'].quantile(0.75)]
    return df.symbol.tolist()


def calculate_bad_assets_ratio(low_liability_list,date):
    """
    计算坏资产比率

    根据资产负债表数据，计算坏资产占总资产的比率，
    并返回比率在20%-80%之间的股票列表。

    参数:
        low_liability_list: 低负债股票代码列表

    返回:
        proper_receivable_list: 坏资产比率在20%-80%之间的股票列表
    """

    # 查询资产负债表数据
    balance_fields = [
        'total_assets',  # 资产总计
        'notes_receiv',  # 应收票据
        'accounts_receiv',  # 应收账款
        'oth_receiv',  # 其他应收款
        'goodwill',  # 商誉
        'intan_assets',  # 无形资产
        'inventories',  # 存货
        'cip'  # 在建工程
    ]

    df = panda_data.get_financial_data(
        symbols=low_liability_list,
        fields=balance_fields,
        end_date = date,
        data_type='balance',
        date_type='end_date'
    )

    if df is None or df.empty:
        logger.error("未能获取资产负债表数据")
        return []

    logger.info(f"获取到 {len(df)} 条资产负债表数据")

    # 填充缺失值为0
    df = df.fillna(0)

    # 计算坏资产 = 应收票据 + 应收账款 + 其他应收款 + 商誉 + 无形资产 + 存货 + 在建工程
    bad_asset_columns = [
        'notes_receiv',
        'accounts_receiv',
        'oth_receiv',
        'good_will',
        'intangible_assets',
        'inventories',
        'constru_in_process'
    ]

    # 确保这些列存在，如果不存在则添加为0
    for col in bad_asset_columns:
        if col not in df.columns:
            df[col] = 0

    df['bad_assets'] = df[bad_asset_columns].sum(axis=1)

    # 计算坏资产比率
    df['ratio'] = df['bad_assets'] / df['total_assets']

    # 按比率排序
    df = df.sort_values(by='ratio')

    # 获取比率在20%-80%之间的股票
    total_count = len(df)
    start_idx = int(0.2 * total_count)
    end_idx = int(0.8 * total_count)

    proper_receivable_list = list(df['symbol'].iloc[start_idx:end_idx])

    logger.info(f"坏资产比率在20%-80%之间的股票数量: {len(proper_receivable_list)}")
    logger.info(f"样本股票: {proper_receivable_list[:5]}")

    return proper_receivable_list


def get_stock_list(context):

    yesterday = str(context.previous_date)
    # 获取上市天数 >= 250 天的股票
    qualified = panda_data.get_stocks_by_listing_days(yesterday, min_trading_days=250)
    qualified = filter_kcb_stock(qualified)
    st_stocks = set(panda_data.get_st_stocks_by_date(yesterday))
    qualified = [x for x in qualified if x not in st_stocks]


    q = query(balance.code, balance.total_liability, balance.total_assets).filter(valuation.code.in_(initial_list))
    df = get_fundamentals(q)
    df = df.dropna()
    df['ratio'] = df['total_liability'] / df['total_assets']
    df = df.sort_values(by='ratio')
    df = df[df['ratio'] < df['ratio'].quantile(0.75)]
    low_liability_list = list(df.code)

    q = query(balance.code,
              balance.total_assets,  # 总资产
              balance.bill_receivable,  # 应收票据
              balance.account_receivable,  # 应收账款
              balance.other_receivable,  # 其他应收款
              balance.good_will,  # 商誉
              balance.intangible_assets,  # 无形资产
              balance.inventories,  # 存货
              balance.constru_in_process,  # 在建工程
              ).filter(balance.code.in_(low_liability_list))
    df = get_fundamentals(q)
    df = df.fillna(0)
    df['bad_assets'] = df.sum(1) - df['total_assets']
    df['ratio'] = df['bad_assets'] / df['total_assets']
    df = df.sort_values(by='ratio')
    proper_receivable_list = list(df.code)[int(0.2 * len(list(df.code))):int(0.8 * len(list(df.code)))]

    df = get_history_fundamentals(proper_receivable_list, fields=[indicator.code, indicator.roe], watch_date=yesterday,
                                  count=5, interval='1q')
    df = df.groupby('code').apply(lambda x: x.reset_index()).roe.unstack()
    df['past_average'] = 0.1 * df.iloc[:, 0] + 0.2 * df.iloc[:, 1] + 0.3 * df.iloc[:, 2] + 0.4 * df.iloc[:, 3]
    df['now_average'] = 0.1 * df.iloc[:, 1] + 0.2 * df.iloc[:, 2] + 0.3 * df.iloc[:, 3] + 0.4 * df.iloc[:, 4]
    df['delta_average'] = df['now_average'] - df['past_average']
    df.dropna(inplace=True)
    df.sort_values(by='delta_average', ascending=False, inplace=True)
    roe_list = list(df.index)[:int(0.1 * len(list(df.index)))]

    q = query(valuation.code, valuation.pb_ratio).filter(balance.code.in_(roe_list)).order_by(valuation.pb_ratio.asc())
    df = get_fundamentals(q)
    df = df[df['pb_ratio'] > 0]
    pb_list = list(df.code)

    final_list = pb_list
    return final_list

def after_trading(context):
    """盘后处理"""
    try:
        account = context.stock_account_dict[context.account]
        positions_count = get_current_positions_count(context)

        SRLogger.info(f"[{context.now}] 收盘后统计：")
        SRLogger.info(f"  - 账户总资产：{account.total_value:.2f}")
        SRLogger.info(f"  - 持仓市值：{account.market_value:.2f}")
        SRLogger.info(f"  - 可用资金：{account.cash:.2f}")
        SRLogger.info(f"  - 持仓股票数：{positions_count}")

        # 显示持仓详情
        if positions_count > 0:
            SRLogger.info(f"  持仓明细：")
            for stock_id, state in context.stock_states.items():
                if state.position_held and state.entry_price:
                    position_size = get_current_position_size(context, stock_id)
                    if position_size > 0 and len(state.price_history) > 0:
                        current_price = state.price_history[-1]['close']
                        profit_ratio = (current_price - state.entry_price) / state.entry_price * 100
                        SRLogger.info(f"    [{stock_id}] 数量={position_size}, "
                                      f"成本={state.entry_price:.2f}, "
                                      f"现价={current_price:.2f}, "
                                      f"盈亏={profit_ratio:+.2f}%")

    except Exception as e:
        SRLogger.error(f"盘后处理失败: {str(e)}")


def on_stock_trade_rtn(context, order, bar_dict):
    """股票交易回报"""
    try:
        side_text = '买入' if order.side == 1 else '卖出'
        SRLogger.info(
            f"✅ 交易回报 - {order.order_book_id}: {side_text} {order.filled_quantity}股 @ {order.avg_price:.2f}元")
    except Exception as e:
        SRLogger.error(f"交易回报处理失败: {str(e)}")


def stock_order_cancel(context, order, bar_dict):
    """股票订单撤销回报"""
    try:
        SRLogger.info(f"订单撤销 - {order.order_book_id}: {order.quantity}股订单被撤销")
    except Exception as e:
        SRLogger.error(f"订单撤销处理失败: {str(e)}")
