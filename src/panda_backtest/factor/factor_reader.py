#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
因子快速读取器 - 用于策略中高效读取因子数据
"""

import sqlite3
from typing import Dict, Optional, List
from pathlib import Path
from common.config.config import config
from panda_backtest.system.panda_log import SRLogger


class FactorReader:
    """因子快速读取器（带内存缓存）"""
    
    def __init__(self, sqlite_path: str = None):
        """
        初始化因子读取器
        
        Args:
            sqlite_path: SQLite数据库路径
        """
        if sqlite_path:
            self.sqlite_path = sqlite_path
        else:
            # 使用项目统一的 SQLite 数据库路径
            try:
                from panda_server.config.env import SQLITE_DB_PATH
                self.sqlite_path = SQLITE_DB_PATH
            except ImportError:
                # 如果无法导入，使用默认路径
                project_root = Path(__file__).resolve().parent.parent.parent.parent
                self.sqlite_path = str(project_root / "data" / "panda_local.db")
        self.cache = {}  # 内存缓存 {symbol_date: factors_dict}
        self.cache_hits = 0
        self.cache_misses = 0
        
        # 验证数据库是否存在
        try:
            conn = sqlite3.connect(self.sqlite_path)
            conn.close()
            SRLogger.info(f"因子读取器初始化成功: {self.sqlite_path}")
        except Exception as e:
            SRLogger.error(f"因子读取器初始化失败: {str(e)}")
    
    def get_factors(self, symbol: str, date: str) -> Optional[Dict]:
        """
        读取指定股票和日期的所有因子
        
        Args:
            symbol: 股票代码
            date: 日期（YYYYMMDD或YYYY-MM-DD格式）
        
        Returns:
            因子字典，如果不存在则返回None
            {
                'symbol': '600519.SH',
                'date': '20250110',
                'resistance_20d': 156.8,
                'breakthrough_signal': 1,
                ...
            }
        """
        # 统一日期格式（去除连字符）
        date_key = str(date).replace('-', '')
        cache_key = f"{symbol}_{date_key}"
        
        # 先查缓存
        if cache_key in self.cache:
            self.cache_hits += 1
            return self.cache[cache_key]
        
        # 缓存未命中，查询数据库
        self.cache_misses += 1
        
        try:
            conn = sqlite3.connect(self.sqlite_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM factor_data 
                WHERE symbol = ? AND date = ?
            """, (symbol, date_key))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                factors = dict(row)
                # 存入缓存
                self.cache[cache_key] = factors
                return factors
            
            return None
            
        except Exception as e:
            SRLogger.error(f"读取因子失败 {symbol} {date_key}: {str(e)}")
            return None
    
    def get_factor_value(self, symbol: str, date: str, factor_name: str, default=None):
        """
        读取单个因子值
        
        Args:
            symbol: 股票代码
            date: 日期
            factor_name: 因子名称
            default: 默认值（如果因子不存在）
        
        Returns:
            因子值或默认值
        """
        factors = self.get_factors(symbol, date)
        if factors:
            return factors.get(factor_name, default)
        return default
    
    def preload_factors(self, symbol_list: list, date_list: list):
        """
        批量预加载因子（提升性能）
        
        Args:
            symbol_list: 股票代码列表
            date_list: 日期列表
        """
        try:
            conn = sqlite3.connect(self.sqlite_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # 构建IN查询
            symbols_placeholder = ','.join(['?' for _ in symbol_list])
            dates_placeholder = ','.join(['?' for _ in date_list])
            
            # 统一日期格式
            formatted_dates = [str(d).replace('-', '') for d in date_list]
            
            cursor.execute(f"""
                SELECT * FROM factor_data 
                WHERE symbol IN ({symbols_placeholder}) 
                AND date IN ({dates_placeholder})
            """, symbol_list + formatted_dates)
            
            rows = cursor.fetchall()
            conn.close()
            
            # 批量写入缓存
            for row in rows:
                factors = dict(row)
                cache_key = f"{factors['symbol']}_{factors['date']}"
                self.cache[cache_key] = factors
            
            SRLogger.info(f"预加载因子完成: {len(rows)} 条记录")
            
        except Exception as e:
            SRLogger.error(f"批量预加载因子失败: {str(e)}")
    
    def clear_cache(self):
        """清空缓存"""
        self.cache.clear()
        self.cache_hits = 0
        self.cache_misses = 0
        SRLogger.info("因子缓存已清空")
    
    def get_cache_stats(self) -> Dict:
        """获取缓存统计信息"""
        total_requests = self.cache_hits + self.cache_misses
        hit_rate = self.cache_hits / total_requests * 100 if total_requests > 0 else 0
        
        return {
            'cache_size': len(self.cache),
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'total_requests': total_requests,
            'hit_rate': round(hit_rate, 2)
        }
    
    def log_cache_stats(self):
        """打印缓存统计信息"""
        stats = self.get_cache_stats()
        SRLogger.info(f"因子缓存统计: 大小={stats['cache_size']}, "
                     f"命中={stats['cache_hits']}, 未命中={stats['cache_misses']}, "
                     f"命中率={stats['hit_rate']}%")

    def get_all_stocks(self) -> List[str]:
        """
        获取全市场股票列表（从因子数据表中提取所有唯一的股票代码）

        Returns:
            股票代码列表
        """
        try:
            conn = sqlite3.connect(self.sqlite_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT DISTINCT symbol FROM factor_data
                ORDER BY symbol
            """)

            rows = cursor.fetchall()
            conn.close()

            stock_list = [row[0] for row in rows]
            SRLogger.info(f"从因子数据获取股票列表: {len(stock_list)} 只股票")
            return stock_list

        except Exception as e:
            SRLogger.error(f"获取股票列表失败: {str(e)}")
            return []

