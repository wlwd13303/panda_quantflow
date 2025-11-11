#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
阻力位因子 - 计算股票的阻力位水平
"""

import pandas as pd
import numpy as np
from ..factor_base import FactorBase
from panda_backtest.system.panda_log import SRLogger


class ResistanceFactor(FactorBase):
    """阻力位因子 - 识别价格阻力位"""
    
    def __init__(self, factor_id: str, params: dict = None):
        super().__init__(factor_id, params)
        self.lookback_period = params.get('lookback_period', 20) if params else 20
    
    def calculate(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        计算阻力位因子
        
        Returns:
            DataFrame: [symbol, date, resistance_20d, resistance_level]
        """
        try:
            # 需要额外的历史数据来计算阻力位
            lookback_days = self.get_lookback_days()
            actual_start = self.get_trading_date_before(start_date, lookback_days)
            
            # 获取价格数据（后复权）
            price_df = self.get_price_data(symbol, actual_start, end_date)
            
            if price_df.empty:
                return pd.DataFrame()
            
            # 按日期排序
            price_df = price_df.sort_values('date').reset_index(drop=True)
            
            result_rows = []
            
            # 从有足够历史数据的位置开始计算
            for i in range(self.lookback_period, len(price_df)):
                current_date = price_df.iloc[i]['date']
                
                # 只保留目标日期范围的结果
                if current_date < start_date or current_date > end_date:
                    continue
                
                # 取最近N天的数据
                recent_data = price_df.iloc[i - self.lookback_period:i]
                highs = recent_data['high_adj'].values
                
                # 识别阻力位（使用与策略相同的逻辑）
                resistance = self._identify_resistance(highs)
                
                result_rows.append({
                    'symbol': symbol,
                    'date': current_date,
                    'resistance_20d': round(resistance, 2),
                    # 'resistance_level': round(resistance, 2)  # 可以扩展其他阻力位算法
                })
            
            return pd.DataFrame(result_rows)
            
        except Exception as e:
            SRLogger.error(f"计算阻力位因子失败 {symbol}: {str(e)}")
            return pd.DataFrame()
    
    def _identify_resistance(self, highs: np.ndarray) -> float:
        """
        识别阻力位（与策略中的逻辑完全一致）
        
        Args:
            highs: 高价数组
            
        Returns:
            阻力位价格
        """
        if len(highs) < 5:
            return max(highs) if len(highs) > 0 else 0.0
        
        # 寻找局部高点作为阻力位
        resistance_candidates = []
        
        for i in range(2, len(highs) - 2):
            # 判断是否为局部高点（前后两天都不高于当前）
            if (highs[i] >= highs[i-1] and highs[i] >= highs[i-2] and
                highs[i] >= highs[i+1] and highs[i] >= highs[i+2]):
                resistance_candidates.append(highs[i])
        
        # 取最小的局部高点作为最近的阻力位
        if resistance_candidates:
            return min(resistance_candidates)
        else:
            return max(highs)
    
    def get_factor_columns(self) -> list:
        """返回因子列名"""
        return ['resistance_20d', 'resistance_level']
    
    def get_lookback_days(self) -> int:
        """需要额外的历史数据天数"""
        # 需要lookback_period天的历史数据，再加5天buffer
        return self.lookback_period + 5

