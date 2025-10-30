#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
财务数据提供者
支持从数据库或 panda_factor 获取财务指标数据
"""

import pandas as pd
import logging
from typing import List, Optional, Dict
from common.connector.mongodb_handler import DatabaseHandler
from common.config.config import config


class FinancialDataProvider:
    """
    财务数据提供者
    支持获取季度财务指标，如 ROE, 净利润等
    """
    
    def __init__(self, db_handler: Optional[DatabaseHandler] = None):
        """
        初始化财务数据提供者
        
        Args:
            db_handler: 数据库处理器，如果不提供则创建新的
        """
        self.logger = logging.getLogger(__name__)
        self.db_handler = db_handler or DatabaseHandler(config=config)
        self.cache = {}  # 数据缓存
        
        # 财务指标字段映射
        self.field_mapping = {
            # ROE 相关
            'q_roe': 'roe',
            'roe': 'roe',
            'return_on_equity': 'roe',
            
            # 利润相关
            'q_profit': 'net_profit',
            'net_profit': 'net_profit',
            'net_income': 'net_profit',
            
            # 营收相关
            'revenue': 'total_revenue',
            'total_revenue': 'total_revenue',
            'operating_revenue': 'total_revenue',
            
            # 资产相关
            'total_assets': 'total_assets',
            'assets': 'total_assets',
            
            # 负债相关
            'total_liabilities': 'total_liabilities',
            'liabilities': 'total_liabilities',
            
            # 其他常用指标
            'eps': 'eps',
            'pe': 'pe_ratio',
            'pb': 'pb_ratio',
            'gross_margin': 'gross_profit_margin',
        }
        
    def get_financial_data(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str,
        fields: List[str],
        collection_name: str = "stock_financial_data"
    ) -> pd.DataFrame:
        """
        从数据库获取财务数据
        
        Args:
            symbols: 股票代码列表，如 ['600519.SH', '000001.SZ']
            start_date: 开始日期，格式 '20240101'
            end_date: 结束日期，格式 '20241231'
            fields: 财务字段列表，如 ['q_roe', 'net_profit']
            collection_name: MongoDB 集合名称
            
        Returns:
            DataFrame with columns: date, symbol, field1, field2, ...
        """
        try:
            # 映射字段名
            mapped_fields = []
            for field in fields:
                mapped = self.field_mapping.get(field.lower(), field)
                mapped_fields.append(mapped)
            
            # 构建查询条件
            query = {
                'symbol': {'$in': symbols},
                'report_date': {
                    '$gte': start_date,
                    '$lte': end_date
                }
            }
            
            # 构建投影（只获取需要的字段）
            projection = {
                '_id': 0,
                'symbol': 1,
                'report_date': 1,
            }
            for field in set(mapped_fields):
                projection[field] = 1
            
            self.logger.info(f"Querying financial data from {collection_name}")
            self.logger.debug(f"Query: {query}")
            self.logger.debug(f"Projection: {projection}")
            
            # 查询数据
            try:
                results = self.db_handler.mongo_find(
                    db_name=config["MONGO_DB"],
                    collection_name=collection_name,
                    query=query,
                    projection=projection
                )
            except Exception as db_error:
                self.logger.warning(f"Collection {collection_name} not found or query failed: {db_error}")
                self.logger.info("Returning empty DataFrame. You may need to:")
                self.logger.info("  1. Import financial data to MongoDB")
                self.logger.info("  2. Or use panda_factor to generate factors separately")
                return pd.DataFrame()
            
            if not results:
                self.logger.warning(f"No financial data found for symbols={symbols}, date_range={start_date}~{end_date}")
                return pd.DataFrame()
            
            # 转换为 DataFrame
            df = pd.DataFrame(results)
            
            # 重命名列
            df.rename(columns={'report_date': 'date'}, inplace=True)
            
            # 反向映射字段名（从数据库字段名映射回用户请求的字段名）
            reverse_mapping = {v: k for k, v in self.field_mapping.items()}
            for i, orig_field in enumerate(fields):
                mapped_field = mapped_fields[i]
                if mapped_field in df.columns and mapped_field != orig_field:
                    df.rename(columns={mapped_field: orig_field}, inplace=True)
            
            self.logger.info(f"Retrieved {len(df)} records")
            return df
            
        except Exception as e:
            self.logger.error(f"Error getting financial data: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()
    
    def get_quarterly_indicator(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str,
        indicator: str
    ) -> pd.DataFrame:
        """
        获取季度财务指标
        
        Args:
            symbols: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            indicator: 指标名称，如 'q_roe', 'net_profit'
            
        Returns:
            DataFrame with columns: date, symbol, indicator_value
        """
        df = self.get_financial_data(
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
            fields=[indicator]
        )
        
        if df.empty:
            return df
        
        # 确保只有需要的列
        if indicator in df.columns:
            df = df[['date', 'symbol', indicator]]
        
        return df
    
    @classmethod
    def create_from_panda_factor(
        cls,
        formulas: List[str],
        symbols: Optional[List[str]] = None,
        start_date: str = "20240101",
        end_date: str = "20241231"
    ) -> pd.DataFrame:
        """
        从 panda_factor 创建因子数据
        这是一个便捷方法，用于在没有本地财务数据时使用 panda_factor
        
        Args:
            formulas: 因子公式列表
            symbols: 股票代码列表（可选）
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            DataFrame with factor data
        """
        try:
            from panda_factor.generate.macro_factor import MacroFactor
            
            logger = logging.getLogger(__name__)
            macro_factor = MacroFactor()
            
            df_factor = macro_factor.create_factor_from_formula_pro(
                factor_logger=logger,
                formulas=formulas,
                symbols=symbols,
                start_date=start_date,
                end_date=end_date
            )
            
            logger.info(f"Created factor data from panda_factor: {df_factor.shape}")
            return df_factor
            
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to create factor from panda_factor: {e}")
            logger.info("Make sure panda_factor is installed and configured correctly")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()


# 全局实例（单例模式）
_financial_data_provider_instance = None


def get_financial_data_provider(db_handler: Optional[DatabaseHandler] = None) -> FinancialDataProvider:
    """
    获取财务数据提供者单例
    
    Args:
        db_handler: 数据库处理器（可选）
        
    Returns:
        FinancialDataProvider 实例
    """
    global _financial_data_provider_instance
    if _financial_data_provider_instance is None:
        _financial_data_provider_instance = FinancialDataProvider(db_handler)
    return _financial_data_provider_instance

