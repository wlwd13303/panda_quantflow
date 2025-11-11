#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
因子计算框架 - 基类定义
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from common.connector.mongodb_handler import DatabaseHandler
from common.config.config import config
from panda_backtest.system.panda_log import SRLogger


class FactorBase(ABC):
    """因子计算基类"""
    
    def __init__(self, factor_id: str, params: Dict[str, Any] = None):
        """
        初始化因子
        
        Args:
            factor_id: 因子唯一标识
            params: 因子参数
        """
        self.factor_id = factor_id
        self.params = params or {}
        self.db_handler = DatabaseHandler(config=config)
        
        # 使用项目统一的 SQLite 数据库路径
        try:
            from panda_server.config.env import SQLITE_DB_PATH
            self.sqlite_path = SQLITE_DB_PATH
        except ImportError:
            # 如果无法导入，使用默认路径
            project_root = Path(__file__).resolve().parent.parent.parent.parent
            self.sqlite_path = str(project_root / "data" / "panda_local.db")
        
    @abstractmethod
    def calculate(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        计算因子值（必须由子类实现）
        
        Args:
            symbol: 股票代码
            start_date: 开始日期（YYYYMMDD）
            end_date: 结束日期（YYYYMMDD）
            
        Returns:
            DataFrame with columns: [symbol, date, factor_value1, factor_value2, ...]
        """
        pass
    
    @abstractmethod
    def get_factor_columns(self) -> List[str]:
        """返回该因子产生的列名"""
        pass

    def get_factor_column_types(self) -> Dict[str, str]:
        """
        返回因子列的数据类型（可选实现）

        Returns:
            Dict[column_name, sqlite_type]: 列名到SQLite数据类型的映射
            支持的类型：INTEGER, REAL, TEXT, BLOB
        """
        # 默认实现：根据列名推断类型
        columns = self.get_factor_columns()
        column_types = {}

        for col in columns:
            if 'signal' in col.lower() or 'position' in col.lower():
                column_types[col] = 'INTEGER'
            elif 'ratio' in col.lower() or 'pct' in col.lower() or col in ['sar']:
                column_types[col] = 'REAL'
            else:
                column_types[col] = 'REAL'  # 默认REAL类型

        return column_types

    @abstractmethod
    def get_lookback_days(self) -> int:
        """返回计算所需的历史数据天数"""
        pass
    
    def get_price_data(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        从数据库获取价格数据（后复权）
        
        Returns:
            DataFrame with columns: [date, open, high, low, close, volume, adj_factor, 
                                    open_adj, high_adj, low_adj, close_adj]
        """
        try:
            # 获取价格数据
            query = {
                "symbol": symbol,
                "date": {"$gte": start_date, "$lte": end_date}
            }
            price_records = self.db_handler.mongo_find(
                db_name=config["MONGO_DB"],
                collection_name="stock_market",
                query=query,
                projection={"_id": 0, "date": 1, "open": 1, "high": 1, 
                           "low": 1, "close": 1, "volume": 1}
            )
            
            if not price_records:
                return pd.DataFrame()
            
            df = pd.DataFrame(price_records)
            df = df.sort_values('date')
            
            # 获取复权因子
            adj_records = self.db_handler.mongo_find(
                db_name=config["MONGO_DB"],
                collection_name="adj_factor",
                query=query,
                projection={"_id": 0, "date": 1, "adj_factor": 1}
            )
            
            if adj_records:
                adj_df = pd.DataFrame(adj_records)
                df = df.merge(adj_df, on='date', how='left')
                df.fillna({'adj_factor': 1.0}, inplace=True)
            else:
                df['adj_factor'] = 1.0
            
            # 后复权调整
            for col in ['open', 'high', 'low', 'close']:
                df[f'{col}_adj'] = df[col] * df['adj_factor']
            
            return df
            
        except Exception as e:
            SRLogger.error(f"获取{symbol}价格数据失败: {str(e)}")
            return pd.DataFrame()
    
    def get_trading_date_before(self, date_str: str, days: int) -> str:
        """
        获取N个交易日之前的日期（简化版，使用自然日*1.5估算）
        
        Args:
            date_str: 日期字符串（YYYYMMDD）
            days: 需要往前推的交易日天数
            
        Returns:
            估算的日期字符串（YYYYMMDD）
        """
        try:
            date = datetime.strptime(date_str, "%Y%m%d")
            # 考虑周末和节假日，往前多推50%的天数
            before_date = date - timedelta(days=int(days * 1.5))
            return before_date.strftime("%Y%m%d")
        except Exception as e:
            SRLogger.error(f"日期计算失败: {str(e)}")
            # 默认往前推90天
            date = datetime.strptime(date_str, "%Y%m%d")
            before_date = date - timedelta(days=90)
            return before_date.strftime("%Y%m%d")

