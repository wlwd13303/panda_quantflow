#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
突破因子 - 检测价格突破+成交量放大信号
"""

import pandas as pd
import numpy as np
from ..factor_base import FactorBase
from panda_backtest.system.panda_log import SRLogger


class BreakthroughFactor(FactorBase):
    """突破因子 - 识别价格突破阻力位并伴随成交量放大"""
    
    def __init__(self, factor_id: str, params: dict = None):
        super().__init__(factor_id, params)
        self.min_breakthrough_percent = params.get('min_breakthrough_percent', 2.0) if params else 2.0
        self.volume_surge_ratio = params.get('volume_surge_ratio', 1.5) if params else 1.5
        self.lookback_period = params.get('lookback_period', 20) if params else 20
    
    def calculate(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        计算突破因子
        
        Returns:
            DataFrame: [symbol, date, breakthrough_signal, breakthrough_ratio, volume_surge_ratio]
        """
        try:
            # 需要额外的历史数据
            lookback_days = self.get_lookback_days()
            actual_start = self.get_trading_date_before(start_date, lookback_days)
            
            # 获取价格数据（后复权）
            price_df = self.get_price_data(symbol, actual_start, end_date)
            
            if price_df.empty:
                return pd.DataFrame()
            
            price_df = price_df.sort_values('date').reset_index(drop=True)
            
            result_rows = []
            
            # 从有足够历史数据的位置开始计算
            for i in range(self.lookback_period, len(price_df)):
                current_date = price_df.iloc[i]['date']
                
                # 只保留目标日期范围的结果
                if current_date < start_date or current_date > end_date:
                    continue
                
                current_price = price_df.iloc[i]['close_adj']
                current_volume = price_df.iloc[i]['volume']
                
                # 计算阻力位（最近N天）
                recent_data = price_df.iloc[i - self.lookback_period:i]
                resistance = self._calc_resistance(recent_data['high_adj'].values)
                
                # 计算平均成交量（最近10天）
                volume_window = min(10, len(recent_data))
                avg_volume = recent_data['volume'].tail(volume_window).mean()
                
                # 突破判断
                breakthrough_ratio = (current_price - resistance) / resistance * 100 if resistance > 0 else 0
                volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0
                
                # 同时满足价格突破和成交量放大才算突破信号
                is_breakthrough = (breakthrough_ratio >= self.min_breakthrough_percent and 
                                 volume_ratio >= self.volume_surge_ratio)
                
                result_rows.append({
                    'symbol': symbol,
                    'date': current_date,
                    'breakthrough_signal': 1 if is_breakthrough else 0,
                    # 'breakthrough_ratio': round(breakthrough_ratio, 2),
                    # 'volume_surge_ratio': round(volume_ratio, 2)
                })
            
            return pd.DataFrame(result_rows)
            
        except Exception as e:
            SRLogger.error(f"计算突破因子失败 {symbol}: {str(e)}")
            return pd.DataFrame()
    
    def _calc_resistance(self, highs: np.ndarray) -> float:
        """
        计算阻力位（与ResistanceFactor保持一致）
        
        Args:
            highs: 高价数组
            
        Returns:
            阻力位价格
        """
        if len(highs) < 5:
            return max(highs) if len(highs) > 0 else 0.0
        
        resistance_candidates = []
        for i in range(2, len(highs) - 2):
            if (highs[i] >= highs[i-1] and highs[i] >= highs[i-2] and
                highs[i] >= highs[i+1] and highs[i] >= highs[i+2]):
                resistance_candidates.append(highs[i])
        
        return min(resistance_candidates) if resistance_candidates else max(highs)
    
    def get_factor_columns(self) -> list:
        """返回因子列名"""
        return ['breakthrough_signal', 'breakthrough_ratio', 'volume_surge_ratio']
    
    def get_lookback_days(self) -> int:
        """需要额外的历史数据天数"""
        # 需要lookback_period天 + 10天成交量计算
        return self.lookback_period + 10

