#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
ROEPB策略 - 基于历史信号的多股票交易策略

策略核心思想：
使用预先生成的个股买卖信号进行多股票交易
- 买入信号：第三阶段信号（'第三' in signal）
- 卖出信号：新卖出信号（'新卖出' in signal）

信号来源：
从 single_stock_results/{stock}/history_signals_20260130.csv 读取历史信号

止盈止损：
- 止盈：相对入场价上涨20%
- 止损：相对入场价下跌10%
"""

from panda_backtest.api.api import *
from panda_backtest.api.stock_api import *
import pandas as pd
import numpy as np
import os
import datetime
import glob


def initialize(context):
    """策略初始化"""
    SRLogger.info("=== 多股票策略初始化 ===")

    # ========== 基础配置 ==========
    context.account = '8888'

    # ========== 策略参数 ==========
    context.take_profit_percent = 20.0  # 止盈比例20%
    context.stop_loss_percent = 8  # 止损比例10%
    context.position_percent = 0.5  # 每次买入占总资产的比例（0.5%）
    context.max_positions = 2000  # 最大持仓股票数量
    context.use_stop_profit = False  # 是否启用止盈（默认关闭，只用信号）
    context.use_stop_loss = False  # 是否启用止损（默认关闭，只用信号）

    # ========== 信号数据 ==========
    # 按日期组织的信号字典：
    # {date: {'buy': {stock_id: {...}}, 'sell': {stock_id: {...}}}}
    context.signals_by_date = {}

    # 股票基础数据（用于获取价格等信息）
    # {stock_id: DataFrame}
    context.stock_data = {}

    # ========== 持仓管理 ==========
    # 多股票持仓字典：{stock_id: {'entry_price': float, 'entry_date': str, 'max_profit_price': float}}
    context.positions = {}

    # ========== 记录管理 ==========
    context.trade_records = []  # 交易记录
    context.daily_records = []  # 每日记录

    # ========== 加载所有股票的信号数据 ==========
    load_all_signals(context)
    # load_all_signals_csv(context)

    SRLogger.info(f"止盈比例: {context.take_profit_percent}%")
    SRLogger.info(f"止损比例: {context.stop_loss_percent}%")
    SRLogger.info(f"单次买入仓位: {context.position_percent}%")
    SRLogger.info(f"最大持仓数: {context.max_positions}")
    SRLogger.info(f"已加载股票数: {len(context.stock_data)}")

    # 统计总信号数和日期范围
    total_buy_signals = sum(len(signals['buy']) for signals in context.signals_by_date.values())
    total_sell_signals = sum(len(signals['sell']) for signals in context.signals_by_date.values())
    SRLogger.info(f"总买入信号数: {total_buy_signals}")
    SRLogger.info(f"总卖出信号数: {total_sell_signals}")
    SRLogger.info(f"信号日期数: {len(context.signals_by_date)}")
    SRLogger.info("=== 初始化完成 ===\n")


def load_all_signals_csv(context):
    """加载所有股票的历史信号数据，并按日期组织"""
    base_dir = "D:/all_data.csv"
    data = pd.read_csv(base_dir)

    loaded_count = 0
    total_buy_signals = 0
    total_sell_signals = 0
    for stock_id, df in data.groupby('symbol'):

        try:

            # 确保 date 列是字符串格式
            df['date'] = df['date'].astype(str)

            # 解析买入信号（第三阶段信号）
            buy_data = df[df['买入']].copy()
            df['卖出'].fillna(False, inplace=True)
            # 解析卖出信号（新卖出信号）
            sell_data = df[df['卖出']].copy()

            # 如果该股票有信号，保存数据
            if not buy_data.empty or not sell_data.empty:
                # 保存股票数据（用于获取价格）
                context.stock_data[stock_id] = df

                # 按日期组织买入信号
                for _, row in buy_data.iterrows():
                    date_str = str(row['date'])

                    # 初始化该日期的信号字典
                    if date_str not in context.signals_by_date:
                        context.signals_by_date[date_str] = {'buy': {}, 'sell': {}}

                    # 添加买入信号
                    context.signals_by_date[date_str]['buy'][stock_id] = {
                        'price': float(row['price']),
                        'signal': str(row['signal']),
                        'stock_name': str(row.get('stock_name', ''))
                    }
                    total_buy_signals += 1

                # 按日期组织卖出信号
                for _, row in sell_data.iterrows():
                    date_str = str(row['date'])

                    # 初始化该日期的信号字典
                    if date_str not in context.signals_by_date:
                        context.signals_by_date[date_str] = {'buy': {}, 'sell': {}}

                    # 添加卖出信号
                    context.signals_by_date[date_str]['sell'][stock_id] = {
                        'price': float(row['price']),
                        'signal': str(row['signal']),
                        'stock_name': str(row.get('stock_name', ''))
                    }
                    total_sell_signals += 1

                loaded_count += 1

                if loaded_count <= 5:  # 只显示前5个股票的详情
                    SRLogger.info(f"✅ {stock_id}: 买入信号={len(buy_data)}, 卖出信号={len(sell_data)}")

        except Exception as e:
            SRLogger.warning(f"⚠️ 加载 {stock_id} 信号失败: {str(e)}")
            continue

    SRLogger.info(f"✅ 成功加载 {loaded_count} 个股票的信号数据")
    SRLogger.info(f"   总买入信号: {total_buy_signals} 个")
    SRLogger.info(f"   总卖出信号: {total_sell_signals} 个")
    SRLogger.info(f"   信号日期数: {len(context.signals_by_date)} 天")


def load_all_signals(context):
    """加载所有股票的历史信号数据，并按日期组织"""
    base_dir = "strategy/single_stock_results4"

    if not os.path.exists(base_dir):
        SRLogger.error(f"❌ 信号目录不存在: {base_dir}")
        return

    # 遍历所有股票目录
    stock_dirs = [d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))]

    loaded_count = 0
    total_buy_signals = 0
    total_sell_signals = 0
    # import pandas as pd
    # df = pd.read_excel("C:\developer\panda_quantflow\股票池26.2.4.xlsx")
    # df['代码'] = df['代码'].astype(str)
    # df['代码'] = df['代码'].apply(lambda x: x.zfill(6))

    # list_symbol = df['代码'].tolist()
    # list_symbol = ['300947']
    for stock_id in stock_dirs:
        # if stock_id[:6] not in  list_symbol:
        #     continue
        signal_file = os.path.join(base_dir, stock_id, "history_signals_20260207.csv")

        if not os.path.exists(signal_file):
            continue

        try:
            # 读取信号数据
            df = pd.read_csv(signal_file)

            # 确保 date 列是字符串格式
            df['date'] = df['date'].astype(str)

            # 解析买入信号（第三阶段信号）
            df['买入'] = df['signal'].apply(lambda x: '买入' in str(x) if pd.notna(x) else False)
            buy_data = df[df['买入']].copy()

            # 解析卖出信号（新卖出信号）
            df['卖出'] = df['signal'].apply(lambda x: '卖出' in str(x) if pd.notna(x) else False)
            sell_data = df[df['卖出']].copy()

            # 如果该股票有信号，保存数据
            if not buy_data.empty or not sell_data.empty:
                # 保存股票数据（用于获取价格）
                context.stock_data[stock_id] = df

                # 按日期组织买入信号
                for _, row in buy_data.iterrows():
                    date_str = str(row['date'])

                    # 初始化该日期的信号字典
                    if date_str not in context.signals_by_date:
                        context.signals_by_date[date_str] = {'buy': {}, 'sell': {}}

                    # 添加买入信号
                    context.signals_by_date[date_str]['buy'][stock_id] = {
                        'price': float(row['price']),
                        'signal': str(row['signal']),
                        'stock_name': str(row.get('stock_name', ''))
                    }
                    total_buy_signals += 1

                # 按日期组织卖出信号
                for _, row in sell_data.iterrows():
                    date_str = str(row['date'])

                    # 初始化该日期的信号字典
                    if date_str not in context.signals_by_date:
                        context.signals_by_date[date_str] = {'buy': {}, 'sell': {}}

                    # 添加卖出信号
                    context.signals_by_date[date_str]['sell'][stock_id] = {
                        'price': float(row['price']),
                        'signal': str(row['signal']),
                        'stock_name': str(row.get('stock_name', ''))
                    }
                    total_sell_signals += 1

                loaded_count += 1

                if loaded_count <= 5:  # 只显示前5个股票的详情
                    SRLogger.info(f"✅ {stock_id}: 买入信号={len(buy_data)}, 卖出信号={len(sell_data)}")

        except Exception as e:
            SRLogger.warning(f"⚠️ 加载 {stock_id} 信号失败: {str(e)}")
            continue

    SRLogger.info(f"✅ 成功加载 {loaded_count} 个股票的信号数据")
    SRLogger.info(f"   总买入信号: {total_buy_signals} 个")
    SRLogger.info(f"   总卖出信号: {total_sell_signals} 个")
    SRLogger.info(f"   信号日期数: {len(context.signals_by_date)} 天")





def get_current_position_size(context, stock_id):
    """获取指定股票的当前持仓数量"""
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
        SRLogger.error(f"获取 {stock_id} 持仓失败: {str(e)}")
        return 0


def execute_buy(context, stock_id, price, signal_info):
    """执行买入操作"""
    try:
        # 检查是否已达到最大持仓数
        if len(context.positions) >= context.max_positions:
            SRLogger.info(f'⚠️ 已达到最大持仓数 {context.max_positions}，跳过买入 {stock_id}')
            return

        # 获取账户信息
        account = context.stock_account_dict.get(context.account)
        if not account:
            SRLogger.error(f"无法获取账户信息")
            return

        # 计算买入金额：总资产 * 仓位比例
        total_value = account.total_value
        buy_amount = total_value * (context.position_percent / 100.0)

        # 计算买入股数（向下取整到100的倍数，A股最小交易单位是100股）
        shares = int(buy_amount / price / 100) * 100
        shares = 500
        # 检查是否至少能买100股
        if shares < 100:
            SRLogger.info(f'⚠️ {stock_id} 资金不足，无法买入至少100股 (需要{price*100:.2f}元，可用{buy_amount:.2f}元)')
            return

        # 使用 order_shares 方式下单
        order_shares(context.account, stock_id, shares)

        # 记录持仓信息
        context.positions[stock_id] = {
            'entry_price': price,
            'entry_date': context.now,
            'max_profit_price': price,
            'signal': signal_info.get('signal', ''),
            'shares': shares
        }

        # 记录交易
        trade_record = {
            'date': context.now,
            'stock_id': stock_id,
            'stock_name': signal_info.get('stock_name', ''),
            'type': '买入',
            'price': price,
            'size': shares,
            'amount': shares * price,
            'position_percent': context.position_percent,
            'signal_type': '第三阶段',
            'signal': signal_info.get('signal', '')
        }
        context.trade_records.append(trade_record)

        SRLogger.info(f'📈 买入 {stock_id}: 价格={price:.2f}, 数量={shares}股, '
                     f'金额={shares*price:.2f}元 ({context.position_percent}%仓位), '
                     f'信号={signal_info.get("signal", "")}')

    except Exception as e:
        SRLogger.error(f"买入 {stock_id} 失败: {str(e)}")


def execute_sell(context, stock_id, price, reason):
    """执行卖出操作"""
    try:
        # 获取当前持仓并卖出
        current_position = get_current_position_size(context, stock_id)
        if current_position > 0:
            order_shares(context.account, stock_id, -current_position)

        # 计算收益
        profit_ratio = 0
        position_info = context.positions.get(stock_id)
        if position_info and position_info['entry_price']:
            entry_price = position_info['entry_price']
            profit_ratio = (price - entry_price) / entry_price * 100

        # 记录交易
        trade_record = {
            'date': context.now,
            'stock_id': stock_id,
            'type': '卖出',
            'price': price,
            'size': current_position,
            'reason': reason,
            'profit_ratio': profit_ratio
        }
        context.trade_records.append(trade_record)

        # 清除持仓记录
        if stock_id in context.positions:
            del context.positions[stock_id]

        SRLogger.info(f'📉 卖出 {stock_id}: {reason}, 价格={price:.2f}, 数量={current_position}, 收益率={profit_ratio:.2f}%')

    except Exception as e:
        SRLogger.error(f"卖出 {stock_id} 失败: {str(e)}")


def handle_data(context, bar_dict):
    """每个Bar的处理逻辑 - 基于ROEPB信号的多股票交易（按日期优化）"""
    current_date = context.now
    # 将日期转换为字符串格式 YYYYMMDD
    if isinstance(current_date, str):
        current_date_str = current_date.replace('-', '')
    else:
        current_date_str = current_date.strftime('%Y%m%d')

    # ========== 获取当天的信号 ==========
    today_signals = context.signals_by_date.get(current_date_str)

    # 如果当天没有任何信号，只需要检查持仓的止盈止损
    if not today_signals:
        # 检查持仓的止盈止损（如果启用）
        if context.use_stop_profit or context.use_stop_loss:
            check_stop_conditions(context, bar_dict, current_date_str)
        return

    # ========== 处理当天的买入信号 ==========
    buy_signals = today_signals.get('buy', {})
    for stock_id, signal_info in buy_signals.items():
        try:
            # 检查是否已持仓
            if stock_id in context.positions:
                continue

            # 检查是否达到最大持仓数
            if len(context.positions) >= context.max_positions:
                SRLogger.info(f'⚠️ 已达到最大持仓数 {context.max_positions}，跳过买入 {stock_id}')
                break

            # 获取行情数据
            if stock_id not in bar_dict:
                continue

            bar = bar_dict[stock_id]
            current_close = float(bar.close)

            # 执行买入
            execute_buy(context, stock_id, current_close, signal_info)

        except Exception as e:
            SRLogger.error(f"处理 {stock_id} 买入信号时出错: {str(e)}")
            continue

    # ========== 处理当天的卖出信号 ==========
    sell_signals = today_signals.get('sell', {})
    for stock_id, signal_info in sell_signals.items():
        try:
            # 检查是否持仓
            if stock_id not in context.positions:
                continue

            # 获取行情数据
            if stock_id not in bar_dict:
                continue

            bar = bar_dict[stock_id]
            current_close = float(bar.close)

            # 执行卖出
            sell_reason = f"ROEPB卖出信号 (信号={signal_info.get('signal', '')})"
            execute_sell(context, stock_id, current_close, sell_reason)

        except Exception as e:
            SRLogger.error(f"处理 {stock_id} 卖出信号时出错: {str(e)}")
            continue

    # ========== 检查持仓的止盈止损（如果启用）==========
    if context.use_stop_profit or context.use_stop_loss:
        check_stop_conditions(context, bar_dict, current_date_str)


def check_stop_conditions(context, bar_dict, current_date_str):
    """检查所有持仓的止盈止损条件"""
    # 遍历所有持仓
    for stock_id in list(context.positions.keys()):  # 使用list避免字典在迭代时被修改
        try:
            # 获取行情数据
            if stock_id not in bar_dict:
                continue

            bar = bar_dict[stock_id]
            current_close = float(bar.close)

            position_info = context.positions[stock_id]
            entry_price = position_info['entry_price']

            # 更新持仓期间最高价格
            position_info['max_profit_price'] = max(
                position_info.get('max_profit_price', current_close),
                current_close
            )

            # 计算收益率
            return_ratio = (current_close - entry_price) / entry_price * 100

            sell_reason = None

            # 止盈条件
            if context.use_stop_profit and return_ratio >= context.take_profit_percent:
                sell_reason = f"止盈 (收益率={return_ratio:.2f}%)"

            # 止损条件
            elif context.use_stop_loss and return_ratio <= -context.stop_loss_percent:
                sell_reason = f"止损 (收益率={return_ratio:.2f}%)"

            # 执行卖出
            if sell_reason:
                execute_sell(context, stock_id, current_close, sell_reason)

        except Exception as e:
            SRLogger.error(f"检查 {stock_id} 止盈止损时出错: {str(e)}")
            continue


def before_trading(context):
    """盘前处理"""
    try:
        account = context.stock_account_dict[context.account]
        position_count = len(context.positions)
        SRLogger.info(f"[{context.now}] 开盘前 - 账户总资产：{account.total_value:.2f}, "
                     f"可用资金：{account.cash:.2f}, 持仓股票数：{position_count}/{context.max_positions}")
    except Exception as e:
        SRLogger.error(f"盘前处理失败: {str(e)}")


def after_trading(context):
    """盘后处理"""
    try:
        account = context.stock_account_dict[context.account]

        # 统计信息
        SRLogger.info(f"[{context.now}] 收盘后统计：")
        SRLogger.info(f"  - 账户总资产：{account.total_value:.2f}")
        SRLogger.info(f"  - 持仓市值：{account.market_value:.2f}")
        SRLogger.info(f"  - 可用资金：{account.cash:.2f}")
        SRLogger.info(f"  - 持仓股票数：{len(context.positions)}")

        # 显示各持仓的盈亏情况
        if context.positions:
            SRLogger.info(f"  持仓明细：")
            current_date_str = context.now.strftime('%Y%m%d')

            for stock_id, position_info in context.positions.items():
                actual_position = get_current_position_size(context, stock_id)
                if actual_position > 0:
                    # 从股票数据获取当前价格
                    stock_df = context.stock_data.get(stock_id)
                    if stock_df is not None:
                        price_data = stock_df[stock_df['date'].astype(str) == current_date_str]
                        if not price_data.empty:
                            current_price = float(price_data.iloc[0]['price'])
                            entry_price = position_info['entry_price']
                            profit_ratio = (current_price - entry_price) / entry_price * 100
                            profit_amount = (current_price - entry_price) * actual_position
                            SRLogger.info(f"    {stock_id}: 持仓{actual_position}股, 成本{entry_price:.2f}, "
                                        f"现价{current_price:.2f}, 盈亏{profit_ratio:+.2f}% ({profit_amount:+.2f}元)")

    except Exception as e:
        SRLogger.error(f"盘后处理失败: {str(e)}")


def on_stock_trade_rtn(context, order, bar_dict):
    """
    股票交易回报
    当订单成交时触发
    """
    try:
        side_text = '买入' if order.side == 1 else '卖出'
        SRLogger.info(f"✅ 交易回报 - {order.order_book_id}: {side_text} {order.filled_quantity}股 @ {order.avg_price:.2f}元")
    except Exception as e:
        SRLogger.error(f"交易回报处理失败: {str(e)}")


def stock_order_cancel(context, order, bar_dict):
    """
    股票订单撤销回报
    当订单被撤销时触发
    """
    try:
        SRLogger.info(f"⚠️ 订单撤销 - {order.order_book_id}: {order.quantity}股订单被撤销")
    except Exception as e:
        SRLogger.error(f"订单撤销处理失败: {str(e)}")



# 我期望每个股票买入时 买入0.5%的仓位 而不是现在的500股