#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
突破策略 - PandaAI Quantflow版本

策略核心思想：
发现股票存在"突破 → 调整 → 再突破 → 再调整"的上涨模式
其中调整期间不会低于上次突破的价格，突破是实质性的

主要特征：
1. 阶梯式上涨 - 支撑位不断抬升
2. 实质性突破 - 有成交量配合的真突破
3. 健康回调 - 调整不破前期突破位

两阶段买入逻辑（SAR窗口期优化）：
- 第一阶段：突破检测（价格突破+成交量放大）→ 开启24天SAR买入窗口期
- 第二阶段：在窗口期内监控SAR转向信号 → SAR从下方转到上方时买入

止盈止损：
- 止盈：相对入场价上涨20%
- 止损：相对入场价下跌30%
- SAR不参与卖出决策（避免过早离场）
"""

from panda_backtest.api.api import *
from panda_backtest.api.stock_api import *
import pandas as pd
import numpy as np
import talib
import datetime


def initialize(context):
    """策略初始化"""
    SRLogger.info("=== 突破策略初始化 ===")
    
    # ========== 基础配置 ==========
    context.account = '8888'
    context.stock_id = "002317.SZ"  # 跟踪的股票代码
    
    # ========== 策略参数 ==========
    context.lookback_period = 20  # 支撑阻力位识别周期
    context.min_breakthrough_percent = 2.0  # 最小突破幅度2%
    context.volume_surge_ratio = 1.5  # 突破时成交量放大倍数
    context.support_holding_period = 5  # 支撑位至少维持的周期数
    context.max_pullback_percent = 5.0  # 最大回调幅度5%
    context.take_profit_percent = 2000.0  # 止盈比例20%
    context.max_drawdown_percent = 10.0  # 盈利后最大回撤比例10%
    context.position_size = 100  # 基础仓位大小（股）
    
    # SAR指标参数
    context.sar_acceleration = 0.02  # SAR加速因子
    context.sar_maximum = 0.2  # SAR最大加速因子
    context.use_sar_filter = True  # 是否使用SAR过滤器
    context.sar_window_days = 24  # 突破后SAR买入窗口期（交易日）
    
    # ========== 状态变量 ==========
    # 价格历史：[{date, high, low, close, volume}, ...]
    context.price_history = []
    
    # 支撑阻力位
    context.current_support = None
    context.current_resistance = None
    
    # SAR相关变量
    context.current_sar = None
    context.prev_sar = None
    context.sar_position = 0  # SAR相对价格位置: 1=上方, -1=下方
    context.prev_sar_position = 0
    context.sar_just_turned_up = False  # SAR是否刚从下方转到上方
    
    # 第一阶段：突破窗口期管理
    context.in_sar_window = False  # 是否在SAR买入窗口期内
    context.window_start_date = None
    context.window_days_count = 0
    context.breakthrough_candidates = []  # 突破候选点列表
    
    # 第二阶段：涨幅窗口期管理（SAR转向后）
    context.price_surge_threshold = 6.0  # 涨幅阈值（%）
    context.surge_window_days = 24  # 涨幅窗口期（交易日）
    context.in_surge_window = False  # 是否在涨幅窗口期内
    context.sar_trigger_price = None  # SAR转向时的价格（基准价）
    context.surge_window_start_date = None  # 涨幅窗口期开始日期
    context.surge_window_days_count = 0  # 涨幅窗口期已过天数
    
    # 持仓管理
    context.entry_price = None  # 入场价格
    context.position_held = False  # 是否持仓
    context.buy_trigger_price = None  # 买入时的基准价（SAR触发价，用于跌破卖出）
    context.max_profit_price = None  # 持仓期间最高价格（用于回撤计算）
    
    # 记录管理
    context.trade_records = []  # 交易记录
    context.daily_records = []  # 每日记录
    
    SRLogger.info(f"股票代码: {context.stock_id}")
    SRLogger.info(f"突破幅度阈值: {context.min_breakthrough_percent}%")
    SRLogger.info(f"成交量放大倍数: {context.volume_surge_ratio}x")
    SRLogger.info(f"阶段1-SAR窗口期: {context.sar_window_days}天")
    SRLogger.info(f"阶段2-涨幅阈值: {context.price_surge_threshold}%")
    SRLogger.info(f"阶段2-涨幅窗口期: {context.surge_window_days}天")
    SRLogger.info(f"止盈比例: {context.take_profit_percent}%")
    SRLogger.info(f"盈利后最大回撤: {context.max_drawdown_percent}%")
    SRLogger.info("=== 初始化完成 ===\n")


def calculate_sar(context):
    """计算SAR指标"""
    if len(context.price_history) < 10:
        return None
    
    # 提取最近的价格数据（最多50个bar）
    recent_data = context.price_history[-50:] if len(context.price_history) >= 50 else context.price_history
    highs = np.array([p['high'] for p in recent_data])
    lows = np.array([p['low'] for p in recent_data])
    
    try:
        # 使用talib计算SAR
        sar = talib.SAR(highs, lows, 
                       acceleration=context.sar_acceleration, 
                       maximum=context.sar_maximum)
        
        # 返回最新的SAR值
        current_sar = sar[-1] if not np.isnan(sar[-1]) else None
        return current_sar
    except Exception as e:
        SRLogger.error(f"SAR计算错误: {str(e)}")
        return None


def update_sar_position(context, current_price):
    """更新SAR位置状态"""
    if context.current_sar is None:
        return
    
    # 保存前一个状态
    context.prev_sar_position = context.sar_position
    context.prev_sar = context.current_sar
    
    # 判断SAR相对价格的位置
    if context.current_sar > current_price:
        context.sar_position = 1  # SAR在价格上方
    else:
        context.sar_position = -1  # SAR在价格下方
    
    # 检查SAR是否刚从下方转到上方
    context.sar_just_turned_up = (context.prev_sar_position == -1 and 
                                   context.sar_position == 1)
    
    if context.sar_just_turned_up:
        SRLogger.info(f'✨ SAR转向信号: SAR从下方({context.prev_sar:.2f})转到上方({context.current_sar:.2f})')


def identify_support_resistance(context):
    """识别当前支撑位和阻力位"""
    if len(context.price_history) < context.lookback_period:
        return None, None
    
    recent_prices = context.price_history[-context.lookback_period:]
    highs = [p['high'] for p in recent_prices]
    lows = [p['low'] for p in recent_prices]
    
    # 寻找局部低点作为支撑位
    support_candidates = []
    for i in range(2, len(lows) - 2):
        if (lows[i] <= lows[i-1] and lows[i] <= lows[i-2] and
            lows[i] <= lows[i+1] and lows[i] <= lows[i+2]):
            support_candidates.append(lows[i])
    
    # 寻找局部高点作为阻力位
    resistance_candidates = []
    for i in range(2, len(highs) - 2):
        if (highs[i] >= highs[i-1] and highs[i] >= highs[i-2] and
            highs[i] >= highs[i+1] and highs[i] >= highs[i+2]):
            resistance_candidates.append(highs[i])
    
    current_support = max(support_candidates) if support_candidates else min(lows)
    current_resistance = min(resistance_candidates) if resistance_candidates else max(highs)
    
    return current_support, current_resistance


def check_basic_breakthrough(context, price, volume):
    """检查基础突破条件（不包含SAR）"""
    if len(context.price_history) < 10:
        return False
    
    # 获取前期成交量数据
    recent_volumes = [p['volume'] for p in context.price_history[-10:]]
    avg_volume = np.mean(recent_volumes)
    
    if context.current_resistance is None:
        return False
    
    # 突破条件检查
    breakthrough_ratio = (price - context.current_resistance) / context.current_resistance * 100
    volume_surge = volume / avg_volume if avg_volume > 0 else 0
    
    # 基础突破有效性判断
    is_price_breakthrough = breakthrough_ratio >= context.min_breakthrough_percent
    is_volume_confirmed = volume_surge >= context.volume_surge_ratio
    
    return is_price_breakthrough and is_volume_confirmed


def update_breakthrough_window(context):
    """更新第一阶段：突破窗口期状态"""
    if context.in_sar_window:
        context.window_days_count += 1
        
        # 检查窗口期是否过期
        if context.window_days_count >= context.sar_window_days:
            context.in_sar_window = False
            context.window_start_date = None
            context.window_days_count = 0
            SRLogger.info(f'⏰ 阶段1-SAR窗口期已过期 ({context.sar_window_days}天)')
            context.breakthrough_candidates.clear()


def update_surge_window(context):
    """更新第二阶段：涨幅窗口期状态"""
    if context.in_surge_window:
        context.surge_window_days_count += 1
        
        # 检查窗口期是否过期
        if context.surge_window_days_count >= context.surge_window_days:
            context.in_surge_window = False
            context.surge_window_start_date = None
            context.surge_window_days_count = 0
            context.sar_trigger_price = None
            SRLogger.info(f'⏰ 阶段2-涨幅窗口期已过期 ({context.surge_window_days}天)，未达到{context.price_surge_threshold}%涨幅')


def add_breakthrough_candidate(context, price, volume):
    """第一阶段：添加突破候选点并开启SAR窗口期"""
    current_date = context.now
    
    # 记录突破候选点
    candidate = {
        'date': current_date,
        'price': price,
        'volume': volume,
        'support': context.current_support,
        'resistance': context.current_resistance
    }
    context.breakthrough_candidates.append(candidate)
    
    # 开启第一阶段：SAR买入窗口期
    if not context.in_sar_window:
        context.in_sar_window = True
        context.window_start_date = current_date
        context.window_days_count = 0
        SRLogger.info(f'🎯 阶段1：突破检测到，开启SAR窗口期 ({context.sar_window_days}天): '
                     f'价格={price:.2f}, 阻力位={context.current_resistance:.2f}')


def start_surge_window(context, price):
    """第二阶段：SAR转向后，开启涨幅窗口期"""
    current_date = context.now
    
    # 记录SAR转向时的价格作为基准
    context.sar_trigger_price = price
    
    # 开启第二阶段：涨幅窗口期
    context.in_surge_window = True
    context.surge_window_start_date = current_date
    context.surge_window_days_count = 0
    
    # 关闭第一阶段窗口期
    context.in_sar_window = False
    context.window_start_date = None
    context.window_days_count = 0
    context.breakthrough_candidates.clear()
    
    SRLogger.info(f'🎯 阶段2：SAR转向确认，开启涨幅窗口期 ({context.surge_window_days}天): '
                 f'基准价={price:.2f}, SAR={context.current_sar:.2f}, '
                 f'目标涨幅≥{context.price_surge_threshold}%')


def is_sar_turn_signal(context):
    """检查SAR是否转向（第一阶段）"""
    if not context.use_sar_filter:
        return True
    
    # 必须在第一阶段窗口期内且SAR刚转向
    return context.in_sar_window and context.sar_just_turned_up


def check_price_surge(context, current_price):
    """检查价格涨幅是否达到阈值（第二阶段）"""
    if not context.in_surge_window or context.sar_trigger_price is None:
        return False
    
    # 计算相对SAR转向价的涨幅
    surge_ratio = (current_price - context.sar_trigger_price) / context.sar_trigger_price * 100
    
    # 判断是否达到涨幅阈值
    if surge_ratio >= context.price_surge_threshold:
        SRLogger.info(f'✅ 阶段2完成：涨幅达标 {surge_ratio:.2f}% (阈值{context.price_surge_threshold}%)')
        SRLogger.info(f'   基准价={context.sar_trigger_price:.2f}, 当前价={current_price:.2f}, '
                     f'窗口期第{context.surge_window_days_count}天')
        return True
    
    return False


def get_current_position_size(context):
    """获取当前持仓数量"""
    try:
        account = context.stock_account_dict.get(context.account)
        if account and hasattr(account, 'positions'):
            # 使用 positions 属性（兼容研报策略的方式）
            position = account.positions.get(context.stock_id)
            if position and hasattr(position, 'quantity'):
                return position.quantity
            # 回退到旧的方式
            if hasattr(account, 'position_dict'):
                position = account.position_dict.get(context.stock_id)
                if position:
                    return position.today_amount + position.enable_amount
        return 0
    except Exception as e:
        SRLogger.error(f"获取持仓失败: {str(e)}")
        return 0


def execute_buy(context, price):
    """执行买入操作（第三阶段）"""
    try:
        # 使用 order_shares 方式下单（与研报策略保持一致）
        order_shares(context.account, context.stock_id, context.position_size)
        
        context.entry_price = price
        context.position_held = True
        
        # 关闭所有窗口期
        context.in_sar_window = False
        context.window_start_date = None
        context.window_days_count = 0
        context.breakthrough_candidates.clear()
        
        context.in_surge_window = False
        context.surge_window_start_date = None
        context.surge_window_days_count = 0
        
        # 计算买入时相对SAR基准价的涨幅
        surge_from_sar = 0
        if context.sar_trigger_price:
            surge_from_sar = (price - context.sar_trigger_price) / context.sar_trigger_price * 100
        
        # 保存买入时的基准价（用于跌破卖出判断）
        context.buy_trigger_price = context.sar_trigger_price if context.sar_trigger_price else price
        context.max_profit_price = price  # 初始化最高价为买入价
        
        # 记录交易
        trade_record = {
            'date': context.now,
            'type': '买入',
            'price': price,
            'size': context.position_size,
            'support': context.current_support,
            'resistance': context.current_resistance,
            'sar': context.current_sar,
            'sar_trigger_price': context.sar_trigger_price,
            'surge_from_sar': surge_from_sar
        }
        context.trade_records.append(trade_record)
        
        sar_info = f', SAR: {context.current_sar:.2f}' if context.current_sar else ''
        surge_info = f', 相对SAR基准涨幅: {surge_from_sar:.2f}%' if context.sar_trigger_price else ''
        SRLogger.info(f'📈 三阶段买入完成: 价格={price:.2f}, 数量={context.position_size}, '
                     f'支撑位={context.current_support:.2f}, 阻力位={context.current_resistance:.2f}{sar_info}{surge_info}')
        SRLogger.info(f'   基准价={context.buy_trigger_price:.2f} (跌破此价将卖出)')
        
        # 清空SAR基准价（但保留buy_trigger_price用于卖出判断）
        context.sar_trigger_price = None
    except Exception as e:
        SRLogger.error(f"买入执行失败: {str(e)}")


def execute_sell(context, price, reason):
    """执行卖出操作"""
    try:
        # 获取当前持仓并卖出（使用负数表示卖出）
        current_position = get_current_position_size(context)
        if current_position > 0:
            order_shares(context.account, context.stock_id, -current_position)
        
        # 计算收益
        profit_ratio = 0
        if context.entry_price:
            profit_ratio = (price - context.entry_price) / context.entry_price * 100
        
        context.entry_price = None
        context.position_held = False
        context.buy_trigger_price = None  # 清空基准价
        context.max_profit_price = None  # 清空最高价
        
        # 记录交易
        trade_record = {
            'date': context.now,
            'type': '卖出',
            'price': price,
            'size': current_position,
            'reason': reason,
            'profit_ratio': profit_ratio,
            'sar': context.current_sar
        }
        context.trade_records.append(trade_record)
        
        sar_info = f', SAR: {context.current_sar:.2f}' if context.current_sar else ''
        SRLogger.info(f'📉 卖出执行: {reason}, 价格={price:.2f}, 数量={current_position}, 收益率={profit_ratio:.2f}%{sar_info}')
    except Exception as e:
        SRLogger.error(f"卖出执行失败: {str(e)}")


def handle_data(context, bar_dict):
    """每个Bar的处理逻辑"""
    current_date = context.now
    
    # ========== 获取当前行情数据 ==========
    try:
        # 优先从 bar_dict 获取行情数据（更高效）
        if context.stock_id in bar_dict:
            bar = bar_dict[context.stock_id]
            current_high = float(bar.high)
            current_low = float(bar.low)
            current_close = float(bar.close)
            current_volume = float(bar.volume)
        else:
            # 如果 bar_dict 中没有，则从数据库查询
            quotation_df = stock_api_quotation(
                symbol_list=[context.stock_id],
                start_date=current_date,
                end_date=current_date,
                period="1d"
            )
            
            if quotation_df.empty:
                SRLogger.warning(f"⚠️ {current_date} 无行情数据")
                return
            
            # 提取当前bar数据
            current_data = quotation_df.iloc[0]
            current_high = float(current_data['high'])
            current_low = float(current_data['low'])
            current_close = float(current_data['close'])
            current_volume = float(current_data['volume'])
        
    except Exception as e:
        SRLogger.error(f"获取行情数据失败: {str(e)}")
        return
    
    # ========== 更新价格历史 ==========
    current_bar = {
        'date': current_date,
        'high': current_high,
        'low': current_low,
        'close': current_close,
        'volume': current_volume
    }
    context.price_history.append(current_bar)
    
    # 保持历史数据长度在100个bar以内
    if len(context.price_history) > 100:
        context.price_history.pop(0)
    
    # ========== 计算技术指标 ==========
    # 计算SAR指标
    context.current_sar = calculate_sar(context)
    
    # 更新SAR位置状态
    if context.current_sar is not None:
        update_sar_position(context, current_close)
    
    # 更新支撑阻力位
    context.current_support, context.current_resistance = identify_support_resistance(context)
    
    # 更新第一阶段窗口期状态
    update_breakthrough_window(context)
    
    # 更新第二阶段窗口期状态
    update_surge_window(context)
    
    # ========== 记录每日状态 ==========
    daily_record = {
        'date': current_date,
        'close_price': current_close,
        'position_held': context.position_held,
        'support_level': context.current_support if context.current_support else 0,
        'resistance_level': context.current_resistance if context.current_resistance else 0,
        'entry_price': context.entry_price if context.entry_price else 0,
        'sar_value': context.current_sar if context.current_sar else 0,
        'sar_position': context.sar_position,
        'sar_just_turned_up': context.sar_just_turned_up,
        'in_sar_window': context.in_sar_window,
        'window_days_count': context.window_days_count,
        'in_surge_window': context.in_surge_window,
        'surge_window_days_count': context.surge_window_days_count,
        'sar_trigger_price': context.sar_trigger_price if context.sar_trigger_price else 0
    }
    context.daily_records.append(daily_record)
    
    # ========== 交易逻辑 ==========
    # 获取实际持仓（用于确认订单执行情况）
    actual_position = get_current_position_size(context)
    
    # 如果没有持仓，寻找买入机会（三阶段买入）
    if not context.position_held or actual_position == 0:
        # 第一阶段：检查基础突破条件，开启SAR窗口期
        if not context.in_sar_window and not context.in_surge_window:
            if check_basic_breakthrough(context, current_close, current_volume):
                add_breakthrough_candidate(context, current_close, current_volume)
        
        # 第二阶段：在SAR窗口期内检查SAR转向信号，开启涨幅窗口期
        elif context.in_sar_window and is_sar_turn_signal(context):
            SRLogger.info(f'✨ 阶段1完成：SAR转向信号触发，窗口期第{context.window_days_count}天')
            start_surge_window(context, current_close)
        
        # 第三阶段：在涨幅窗口期内检查涨幅是否达标
        elif context.in_surge_window and check_price_surge(context, current_close):
            execute_buy(context, current_close)
    
    # 如果有持仓，检查卖出条件
    else:
        if context.entry_price is None:
            return
        
        # 更新持仓期间最高价格（用于回撤计算）
        if context.max_profit_price is None:
            context.max_profit_price = current_close
        else:
            context.max_profit_price = max(context.max_profit_price, current_close)
        
        # 计算收益率
        return_ratio = (current_close - context.entry_price) / context.entry_price * 100
        
        sell_reason = None
        
        # 卖出条件1：跌破基准价（SAR触发价）
        if context.buy_trigger_price and current_close < context.buy_trigger_price:
            sell_reason = f"跌破基准价 (当前价={current_close:.2f}, 基准价={context.buy_trigger_price:.2f})"
        
        # 卖出条件2：止盈条件
        elif return_ratio >= context.take_profit_percent:
            sell_reason = f"止盈 (收益率={return_ratio:.2f}%)"
        
        # 卖出条件3：盈利后回撤10%
        elif return_ratio > 0 and context.max_profit_price:
            # 计算从最高点的回撤
            drawdown_from_peak = (context.max_profit_price - current_close) / context.max_profit_price * 100
            if drawdown_from_peak >= context.max_drawdown_percent:
                sell_reason = f"盈利回撤 (最高价={context.max_profit_price:.2f}, 当前价={current_close:.2f}, 回撤={drawdown_from_peak:.2f}%)"
        
        # 执行卖出
        if sell_reason:
            execute_sell(context, current_close, sell_reason)


def before_trading(context):
    """盘前处理"""
    try:
        account = context.stock_account_dict[context.account]
        SRLogger.info(f"[{context.now}] 开盘前 - 账户总资产：{account.total_value:.2f}, "
                     f"可用资金：{account.cash:.2f}, 持仓状态：{'有持仓' if context.position_held else '空仓'}")
        
        # 显示窗口期信息
        if context.in_sar_window:
            SRLogger.info(f"  ⏰ 阶段1-SAR窗口期：第{context.window_days_count}/{context.sar_window_days}天")
        elif context.in_surge_window:
            current_surge = 0
            if context.sar_trigger_price and len(context.price_history) > 0:
                current_price = context.price_history[-1]['close']
                current_surge = (current_price - context.sar_trigger_price) / context.sar_trigger_price * 100
            SRLogger.info(f"  ⏰ 阶段2-涨幅窗口期：第{context.surge_window_days_count}/{context.surge_window_days}天, "
                         f"当前涨幅：{current_surge:.2f}% (目标≥{context.price_surge_threshold}%)")
    except Exception as e:
        SRLogger.error(f"盘前处理失败: {str(e)}")


def after_trading(context):
    """盘后处理"""
    try:
        account = context.stock_account_dict[context.account]
        current_position = get_current_position_size(context)
        
        # 统计信息
        SRLogger.info(f"[{context.now}] 收盘后统计：")
        SRLogger.info(f"  - 账户总资产：{account.total_value:.2f}")
        SRLogger.info(f"  - 持仓市值：{account.market_value:.2f}")
        SRLogger.info(f"  - 可用资金：{account.cash:.2f}")
        SRLogger.info(f"  - 持仓数量：{current_position} 股")
        
        # 如果有持仓，显示盈亏情况
        if current_position > 0 and context.entry_price:
            # 尝试获取当前价格
            if len(context.price_history) > 0:
                current_price = context.price_history[-1]['close']
                profit_ratio = (current_price - context.entry_price) / context.entry_price * 100
                profit_amount = (current_price - context.entry_price) * current_position
                SRLogger.info(f"  - 浮动盈亏：{profit_ratio:.2f}% ({profit_amount:+.2f}元)")
        
        # 显示支撑阻力位
        if context.current_support and context.current_resistance:
            SRLogger.info(f"  - 支撑位：{context.current_support:.2f}, 阻力位：{context.current_resistance:.2f}")
        
        # 显示SAR信息
        if context.current_sar:
            sar_pos = "上方" if context.sar_position == 1 else "下方" if context.sar_position == -1 else "未确定"
            SRLogger.info(f"  - SAR值：{context.current_sar:.2f} (在价格{sar_pos})")
        
        # 显示涨幅窗口期信息
        if context.in_surge_window and context.sar_trigger_price:
            if len(context.price_history) > 0:
                current_price = context.price_history[-1]['close']
                surge = (current_price - context.sar_trigger_price) / context.sar_trigger_price * 100
                SRLogger.info(f"  - 涨幅窗口期：第{context.surge_window_days_count}天，"
                             f"基准价={context.sar_trigger_price:.2f}，"
                             f"当前涨幅={surge:.2f}% (目标≥{context.price_surge_threshold}%)")
            
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


# ========== 策略说明文档 ==========
"""
突破策略说明（三阶段买入优化版 v3.0）：

1. 策略参数：
   - 支撑阻力位识别周期：20天
   - 最小突破幅度：2%
   - 成交量放大倍数：1.5倍
   - 支撑位维持周期：5天
   - 最大回调幅度：5%
   - 止盈比例：20%
   - 盈利后最大回撤：10%
   - SAR加速因子：0.02
   - SAR最大加速因子：0.2
   - 阶段1-SAR窗口期：24个交易日
   - 阶段2-涨幅阈值：6%
   - 阶段2-涨幅窗口期：24个交易日

2. 三阶段买入逻辑（更严格的买入条件）：⭐ 新增
   
   **第一阶段：突破检测 → 开启SAR窗口期**
   - 动态识别支撑位和阻力位（基于局部高低点）
   - 价格突破阻力位且幅度 ≥ 2%
   - 突破时成交量放大 ≥ 1.5倍
   - 满足条件时开启24天SAR窗口期
   
   **第二阶段：SAR转向 → 开启涨幅窗口期**
   - 在24天窗口期内监控SAR转向信号
   - SAR从价格下方转到上方时：
     * 记录当前价格作为基准价
     * 开启新的24天涨幅窗口期
     * 关闭SAR窗口期
   
   **第三阶段：涨幅达标 → 执行买入** ⭐ 核心创新
   - 在涨幅窗口期内监控价格变化
   - 当价格相对SAR基准价上涨 ≥ 6% 时执行买入
   - 买入后关闭所有窗口期

3. 开仓逻辑优势：
   - **三重验证**：突破确认 → SAR转向 → 涨幅达标
   - **避免假突破**：SAR转向后继续上涨才买入
   - **趋势确认**：6%涨幅确保趋势真实性
   - **时机优化**：在趋势明确后入场，提高胜率
   - **灵活时间**：两个24天窗口期，总计最多48天观察期

4. 卖出逻辑（三条件卖出机制）：⭐ 更新
   - **条件1：跌破基准价**：买入后如果价格跌破SAR触发价（基准价），立即卖出
   - **条件2：止盈**：相对入场价上涨20%
   - **条件3：盈利回撤**：买入且盈利后，从最高点回撤10%立即卖出
   - **已取消30%止损**：不再使用固定止损比例
   - **SAR不参与卖出决策**：避免过早离场 ⭐

5. 风险控制：
   - 单次交易固定仓位
   - 三重卖出条件保护（跌破基准价、止盈、盈利回撤）
   - 两个24天窗口期限制（阶段1+阶段2）
   - 三重买入条件过滤
   - 基准价保护机制（跌破即卖出）

6. 策略优势：
   - **更高胜率**：三阶段过滤减少假突破 ⭐
   - **趋势确认**：6%涨幅保证趋势真实性 ⭐
   - **风险可控**：更严格的买入条件
   - **避免追高**：SAR+涨幅双重确认
   - 完善的窗口期管理
   - 适合中长线趋势操作

7. SAR指标应用：
   - **第一阶段验证**：确认突破后的趋势方向
   - **第二阶段触发**：SAR转向开启涨幅观察期
   - **窗口期管理**：24+24天双窗口机制
   - **不参与卖出**：避免震荡期间频繁转向造成过早离场

8. 使用方式：
   - 在PandaAI Quantflow的股票回测节点中，将本策略代码粘贴到"策略代码"输入框
   - 设置回测参数：初始资金、基准指数、佣金率、回测日期等
   - 调整参数：
     * context.price_surge_threshold = 6.0  # 涨幅阈值（可调）
     * context.surge_window_days = 24       # 涨幅窗口期（可调）
   - 运行回测，查看回测结果和交易记录
   
9. 注意事项：
   - 买入条件更严格，交易频率会降低
   - 适合强趋势股票，震荡股可能无法入场
   - 总观察期最长可达48天（24+24）
   - 6%涨幅阈值可根据股票特性调整（建议范围3-10%）
   - 适合中长线趋势操作，重质量不重数量

10. 版本更新：
   - v3.1 (2025-11): 优化卖出逻辑：增加跌破基准价卖出、取消30%止损、增加盈利回撤10%卖出
   - v3.0 (2025-11): 增加三阶段买入逻辑，涨幅确认机制
   - v2.0 (2025-11): 两阶段SAR窗口期优化
   - v1.0 (2025-05): 基础突破策略
"""

