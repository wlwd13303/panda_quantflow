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
    context.stock_id = "603207.SH"  # 跟踪的股票代码
    
    # ========== 策略参数 ==========
    context.lookback_period = 20  # 支撑阻力位识别周期
    context.min_breakthrough_percent = 2.0  # 最小突破幅度2%
    context.volume_surge_ratio = 1.5  # 突破时成交量放大倍数
    context.support_holding_period = 5  # 支撑位至少维持的周期数
    context.max_pullback_percent = 5.0  # 最大回调幅度5%
    context.take_profit_percent = 20.0  # 止盈比例20%
    context.stop_loss_percent = 30.0  # 止损比例30%
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
    
    # 突破窗口期管理
    context.in_sar_window = False  # 是否在SAR买入窗口期内
    context.window_start_date = None
    context.window_days_count = 0
    context.breakthrough_candidates = []  # 突破候选点列表
    
    # 持仓管理
    context.entry_price = None  # 入场价格
    context.position_held = False  # 是否持仓
    
    # 记录管理
    context.trade_records = []  # 交易记录
    context.daily_records = []  # 每日记录
    
    SRLogger.info(f"股票代码: {context.stock_id}")
    SRLogger.info(f"突破幅度阈值: {context.min_breakthrough_percent}%")
    SRLogger.info(f"成交量放大倍数: {context.volume_surge_ratio}x")
    SRLogger.info(f"SAR买入窗口期: {context.sar_window_days}天")
    SRLogger.info(f"止盈比例: {context.take_profit_percent}%")
    SRLogger.info(f"止损比例: {context.stop_loss_percent}%")
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
    """更新突破窗口期状态"""
    if context.in_sar_window:
        context.window_days_count += 1
        
        # 检查窗口期是否过期
        if context.window_days_count >= context.sar_window_days:
            context.in_sar_window = False
            context.window_start_date = None
            context.window_days_count = 0
            SRLogger.info(f'⏰ SAR买入窗口期已过期 ({context.sar_window_days}天)')
            context.breakthrough_candidates.clear()


def add_breakthrough_candidate(context, price, volume):
    """添加突破候选点并开启窗口期"""
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
    
    # 开启SAR买入窗口期
    if not context.in_sar_window:
        context.in_sar_window = True
        context.window_start_date = current_date
        context.window_days_count = 0
        SRLogger.info(f'突破检测到，开启SAR买入窗口期 ({context.sar_window_days}天): '
                     f'价格={price:.2f}, 阻力位={context.current_resistance:.2f}')


def is_sar_buy_signal(context):
    """检查SAR是否给出买入信号"""
    if not context.use_sar_filter:
        return True
    
    # 必须在窗口期内且SAR刚转向
    return context.in_sar_window and context.sar_just_turned_up


def check_breakthrough_validity(context):
    """检查突破的有效性 - 窗口期内SAR确认"""
    if context.in_sar_window and is_sar_buy_signal(context):
        SRLogger.info(f'✅ SAR买入信号触发: 窗口期第{context.window_days_count}天')
        return True
    return False


def get_current_position_size(context):
    """获取当前持仓数量"""
    try:
        account = context.stock_account_dict.get(context.account)
        if account and hasattr(account, 'position_dict'):
            position = account.position_dict.get(context.stock_id)
            if position:
                return position.today_amount + position.enable_amount
        return 0
    except Exception as e:
        SRLogger.error(f"获取持仓失败: {str(e)}")
        return 0


def execute_buy(context, price):
    """执行买入操作"""
    try:
        orders = {context.stock_id: context.position_size}
        target_stock_group_order(context.account, orders, 0)
        
        context.entry_price = price
        context.position_held = True
        
        # 关闭窗口期
        context.in_sar_window = False
        context.window_start_date = None
        context.window_days_count = 0
        context.breakthrough_candidates.clear()
        
        # 记录交易
        trade_record = {
            'date': context.now,
            'type': '买入',
            'price': price,
            'size': context.position_size,
            'support': context.current_support,
            'resistance': context.current_resistance,
            'sar': context.current_sar
        }
        context.trade_records.append(trade_record)
        
        sar_info = f', SAR: {context.current_sar:.2f}' if context.current_sar else ''
        SRLogger.info(f'📈 买入执行: 价格={price:.2f}, 数量={context.position_size}, '
                     f'支撑位={context.current_support:.2f}, 阻力位={context.current_resistance:.2f}{sar_info}')
    except Exception as e:
        SRLogger.error(f"买入执行失败: {str(e)}")


def execute_sell(context, price, reason):
    """执行卖出操作"""
    try:
        # 清空持仓
        orders = {context.stock_id: 0}
        target_stock_group_order(context.account, orders, 0)
        
        # 计算收益
        profit_ratio = 0
        if context.entry_price:
            profit_ratio = (price - context.entry_price) / context.entry_price * 100
        
        context.entry_price = None
        context.position_held = False
        
        # 记录交易
        trade_record = {
            'date': context.now,
            'type': '卖出',
            'price': price,
            'reason': reason,
            'profit_ratio': profit_ratio,
            'sar': context.current_sar
        }
        context.trade_records.append(trade_record)
        
        sar_info = f', SAR: {context.current_sar:.2f}' if context.current_sar else ''
        SRLogger.info(f'📉 卖出执行: {reason}, 价格={price:.2f}, 收益率={profit_ratio:.2f}%{sar_info}')
    except Exception as e:
        SRLogger.error(f"卖出执行失败: {str(e)}")


def handle_data(context, bar_dict):
    """每个Bar的处理逻辑"""
    current_date = context.now
    
    # ========== 获取当前行情数据 ==========
    try:
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
    
    # 更新突破窗口期状态
    update_breakthrough_window(context)
    
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
        'window_days_count': context.window_days_count
    }
    context.daily_records.append(daily_record)
    
    # ========== 交易逻辑 ==========
    # 获取实际持仓（用于确认订单执行情况）
    actual_position = get_current_position_size(context)
    
    # 如果没有持仓，寻找买入机会
    if not context.position_held or actual_position == 0:
        # 第一阶段：检查基础突破条件，开启窗口期
        if not context.in_sar_window and check_basic_breakthrough(context, current_close, current_volume):
            add_breakthrough_candidate(context, current_close, current_volume)
        
        # 第二阶段：在窗口期内检查SAR买入信号
        elif check_breakthrough_validity(context):
            SRLogger.info(f'💡 SAR买入条件满足: 价格={current_close:.2f}, SAR={context.current_sar:.2f}')
            execute_buy(context, current_close)
    
    # 如果有持仓，检查卖出条件
    else:
        if context.entry_price is None:
            return
        
        # 计算收益率
        return_ratio = (current_close - context.entry_price) / context.entry_price * 100
        
        sell_reason = None
        
        # 止盈条件
        if return_ratio >= context.take_profit_percent:
            sell_reason = f"止盈 (收益率={return_ratio:.2f}%)"
        
        # 止损条件
        elif return_ratio <= -context.stop_loss_percent:
            sell_reason = f"止损 (收益率={return_ratio:.2f}%)"
        
        # 执行卖出
        if sell_reason:
            execute_sell(context, current_close, sell_reason)


def before_trading(context):
    """盘前处理（可选）"""
    pass


def after_trading(context):
    """盘后处理（可选）"""
    pass


# ========== 策略说明文档 ==========
"""
突破策略说明（SAR窗口期买入优化版）：

1. 策略参数：
   - 支撑阻力位识别周期：20天
   - 最小突破幅度：2%
   - 成交量放大倍数：1.5倍
   - 支撑位维持周期：5天
   - 最大回调幅度：5%
   - 止盈比例：20%
   - 止损比例：30%
   - SAR加速因子：0.02
   - SAR最大加速因子：0.2
   - SAR买入窗口期：24个交易日

2. 两阶段买入逻辑（窗口期优化）：
   **第一阶段：突破检测**
   - 动态识别支撑位和阻力位（基于局部高低点）
   - 价格突破阻力位且幅度超过2%
   - 突破时成交量放大1.5倍以上
   - 满足条件时开启24天SAR买入窗口期

   **第二阶段：SAR买入**
   - 在24天窗口期内监控SAR转向信号
   - SAR从价格下方转到上方时立即买入
   - 买入后关闭窗口期

3. 开仓逻辑：
   - 两阶段验证：先突破确认，再SAR时机优化
   - 给SAR更多时间窗口来提供买入信号
   - 避免错过突破后的SAR转向机会
   - 记录入场价格和当时的支撑阻力位及SAR值

4. 止盈止损逻辑（不使用SAR）：
   - 止盈：相对入场价上涨20%
   - 止损：相对入场价下跌30%
   - **SAR不参与卖出决策，避免过早离场** ⭐

5. 风险控制：
   - 单次交易固定仓位
   - 严格的止盈止损机制
   - 24天窗口期限制，避免无限等待

6. 策略优势：
   - **分离突破确认和买入时机** ⭐ 核心创新
   - **增加买入机会**：24天窗口期提供更多SAR转向机会
   - **时机优化**：突破确认趋势，SAR优化入场点
   - **风险可控**：有明确的窗口期限制
   - 完善的风险控制机制
   - 适合趋势性行情

7. SAR指标应用：
   - **买入时机优化**：在确认突破的前提下，等待最佳SAR转向时机
   - **窗口期管理**：24天内有效，过期自动清除
   - **不参与卖出**：避免震荡期间频繁转向造成过早离场

8. 使用方式：
   - 在PandaAI Quantflow的股票回测节点中，将本策略代码粘贴到"策略代码"输入框
   - 设置回测参数：初始资金、基准指数、佣金率、回测日期等
   - 运行回测，查看回测结果和交易记录
   
9. 注意事项：
   - 突破后24天内必须出现SAR转向信号
   - 适合有一定波动性的股票
   - 窗口期可能会错过一些立即的突破机会
   - 适合中长线趋势操作，重质量不重速度
"""

