#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
因子管理器 - 负责因子的CRUD和计算调度
"""

import sqlite3
import json
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
import importlib
from pathlib import Path
from common.connector.mongodb_handler import DatabaseHandler
from common.config.config import config
from panda_backtest.system.panda_log import SRLogger


class FactorManager:
    """因子管理器 - 负责因子的CRUD操作"""
    
    def __init__(self, sqlite_path: str = None):
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
        
        self._init_database()
    
    def _init_database(self):
        """初始化数据库表"""
        # 确保数据库目录存在
        db_dir = os.path.dirname(self.sqlite_path)
        if db_dir and not os.path.exists(db_dir):
            try:
                os.makedirs(db_dir, exist_ok=True)
                self._safe_log(f"创建数据库目录: {db_dir}")
            except Exception as e:
                self._safe_log(f"创建数据库目录失败: {str(e)}", level="error")
                raise
        
        conn = sqlite3.connect(self.sqlite_path)
        cursor = conn.cursor()

        # 检查并升级数据库表结构
        self._upgrade_database_schema(cursor)

        # 创建表（如果不存在）
        cursor.executescript("""
            -- 因子元数据表
            CREATE TABLE IF NOT EXISTS factor_metadata (
                factor_id TEXT PRIMARY KEY,
                factor_name TEXT NOT NULL,
                factor_desc TEXT,
                factor_type TEXT NOT NULL,
                calculation_class TEXT NOT NULL,
                params TEXT,
                status TEXT DEFAULT 'inactive',
                coverage_start_date TEXT,
                coverage_end_date TEXT,
                last_calculation_time TEXT,
                calculation_duration REAL,
                total_records INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            -- 因子数据表（动态宽表设计）
            CREATE TABLE IF NOT EXISTS factor_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                date TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(symbol, date)
            );

            -- 因子列定义表
            CREATE TABLE IF NOT EXISTS factor_columns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                factor_id TEXT NOT NULL,
                column_name TEXT NOT NULL,
                column_type TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(factor_id, column_name)
            );
            
            -- 因子计算日志表
            CREATE TABLE IF NOT EXISTS factor_calculation_log (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                factor_id TEXT NOT NULL,
                calculation_type TEXT NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                status TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT,
                duration REAL,
                processed_records INTEGER DEFAULT 0,
                success_records INTEGER DEFAULT 0,
                failed_records INTEGER DEFAULT 0,
                error_message TEXT,
                created_at TEXT NOT NULL
            );
        """)
        
        # 创建索引
        cursor.executescript("""
            CREATE INDEX IF NOT EXISTS idx_factor_data_symbol ON factor_data(symbol);
            CREATE INDEX IF NOT EXISTS idx_factor_data_date ON factor_data(date);
            CREATE INDEX IF NOT EXISTS idx_factor_data_symbol_date ON factor_data(symbol, date);
            CREATE INDEX IF NOT EXISTS idx_calculation_log_factor_id ON factor_calculation_log(factor_id);
            CREATE INDEX IF NOT EXISTS idx_calculation_log_status ON factor_calculation_log(status);
        """)
        
        conn.commit()
        conn.close()
        self._safe_log(f"因子数据库初始化完成: {self.sqlite_path}")

    def _upgrade_database_schema(self, cursor):
        """数据库表结构初始化（动态列管理）"""
        # 不需要复杂的升级逻辑，直接使用新的动态列管理
        self._safe_log("使用动态列管理系统")

    def _safe_log(self, message: str, level: str = "info"):
        """安全的日志记录（防止SRLogger未初始化）"""
        try:
            if hasattr(SRLogger, '_log_queue') and SRLogger._log_queue is not None:
                # SRLogger 已初始化，使用它
                if level == "error":
                    SRLogger.error(message)
                elif level == "warn":
                    SRLogger.warn(message)
                else:
                    SRLogger.info(message)
            else:
                # SRLogger 未初始化，使用 print
                print(f"[FactorManager] {message}")
        except Exception:
            # 如果日志记录失败，静默处理
            print(f"[FactorManager] {message}")
    
    def register_factor(self, factor_id: str, factor_name: str, 
                       calculation_class: str, factor_type: str = "technical",
                       factor_desc: str = "", params: Dict = None) -> bool:
        """
        注册新因子
        
        Args:
            factor_id: 因子ID（唯一）
            factor_name: 因子名称
            calculation_class: 计算类名（完整路径）
            factor_type: 因子类型
            factor_desc: 因子描述
            params: 因子参数
        """
        try:
            conn = sqlite3.connect(self.sqlite_path)
            cursor = conn.cursor()
            
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            params_json = json.dumps(params) if params else "{}"
            
            cursor.execute("""
                INSERT OR REPLACE INTO factor_metadata 
                (factor_id, factor_name, factor_desc, factor_type, calculation_class, 
                 params, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, 'inactive', ?, ?)
            """, (factor_id, factor_name, factor_desc, factor_type, 
                  calculation_class, params_json, now, now))
            
            conn.commit()
            conn.close()
            
            self._safe_log(f"因子注册成功: {factor_id} - {factor_name}")
            return True
            
        except Exception as e:
            self._safe_log(f"因子注册失败: {str(e)}", level="error")
            return False
    
    def get_factor_metadata(self, factor_id: str = None) -> List[Dict]:
        """获取因子元数据"""
        try:
            conn = sqlite3.connect(self.sqlite_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if factor_id:
                cursor.execute("SELECT * FROM factor_metadata WHERE factor_id = ?", (factor_id,))
            else:
                cursor.execute("SELECT * FROM factor_metadata ORDER BY created_at DESC")
            
            rows = cursor.fetchall()
            conn.close()
            
            return [dict(row) for row in rows]
            
        except Exception as e:
            self._safe_log(f"获取因子元数据失败: {str(e)}", level="error")
            return []
    
    def delete_factor_data(self, factor_id: str, start_date: str = None, 
                          end_date: str = None) -> bool:
        """
        删除因子数据
        
        Args:
            factor_id: 因子ID
            start_date: 开始日期（可选，不指定则删除全部）
            end_date: 结束日期（可选）
        """
        try:
            # 获取因子的列名
            metadata = self.get_factor_metadata(factor_id)
            if not metadata:
                self._safe_log(f"因子不存在: {factor_id}", level="error")
                return False
            
            conn = sqlite3.connect(self.sqlite_path)
            cursor = conn.cursor()
            
            # 获取因子列名
            factor_columns = self._get_factor_columns(factor_id)
            if not factor_columns:
                self._safe_log(f"无法确定因子列: {factor_id}", level="error")
                return False
            
            # 构建SET子句（将对应列设置为NULL）
            set_clause = ", ".join([f"{col} = NULL" for col in factor_columns])
            
            if start_date and end_date:
                sql = f"UPDATE factor_data SET {set_clause} WHERE date >= ? AND date <= ?"
                cursor.execute(sql, (start_date, end_date))
                self._safe_log(f"删除因子数据: {factor_id}, 日期范围: {start_date} ~ {end_date}")
            elif start_date:
                sql = f"UPDATE factor_data SET {set_clause} WHERE date >= ?"
                cursor.execute(sql, (start_date,))
                self._safe_log(f"删除因子数据: {factor_id}, 开始日期: {start_date}")
            else:
                sql = f"UPDATE factor_data SET {set_clause}"
                cursor.execute(sql)
                self._safe_log(f"删除因子全部数据: {factor_id}")
            
            # 更新元数据
            cursor.execute("""
                UPDATE factor_metadata 
                SET status = 'inactive', updated_at = ?
                WHERE factor_id = ?
            """, (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), factor_id))
            
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            self._safe_log(f"删除因子数据失败: {str(e)}", level="error")
            return False
    
    def _get_factor_columns(self, factor_id: str) -> List[str]:
        """获取因子对应的数据列（从数据库动态获取）"""
        try:
            conn = sqlite3.connect(self.sqlite_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT column_name FROM factor_columns
                WHERE factor_id = ?
                ORDER BY column_name
            """, (factor_id,))

            columns = [row[0] for row in cursor.fetchall()]
            conn.close()

            return columns
        except Exception as e:
            self._safe_log(f"获取因子列失败 {factor_id}: {str(e)}", level="error")
            return []

    def _ensure_factor_columns(self, factor_id: str, factor_instance) -> bool:
        """确保因子列在数据库中存在，如果不存在则创建"""
        try:
            conn = sqlite3.connect(self.sqlite_path)
            cursor = conn.cursor()

            # 获取因子声明的列
            factor_columns = factor_instance.get_factor_columns()
            column_types = factor_instance.get_factor_column_types()

            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # 为每个因子列创建记录
            for col_name in factor_columns:
                col_type = column_types.get(col_name, 'REAL')

                # 检查列是否已存在于factor_columns表
                cursor.execute("""
                    SELECT id FROM factor_columns
                    WHERE factor_id = ? AND column_name = ?
                """, (factor_id, col_name))

                if not cursor.fetchone():
                    # 插入列定义
                    cursor.execute("""
                        INSERT INTO factor_columns
                        (factor_id, column_name, column_type, created_at)
                        VALUES (?, ?, ?, ?)
                    """, (factor_id, col_name, col_type, now))

                    # 检查factor_data表是否已有该列，如果没有则添加
                    cursor.execute("PRAGMA table_info(factor_data)")
                    existing_columns = [row[1] for row in cursor.fetchall()]

                    if col_name not in existing_columns:
                        try:
                            cursor.execute(f"ALTER TABLE factor_data ADD COLUMN {col_name} {col_type}")
                            self._safe_log(f"为因子 {factor_id} 添加数据库列: {col_name} ({col_type})")
                        except Exception as e:
                            self._safe_log(f"添加列失败 {factor_id}.{col_name}: {str(e)}", level="error")
                            return False

            conn.commit()
            conn.close()
            return True

        except Exception as e:
            self._safe_log(f"确保因子列失败 {factor_id}: {str(e)}", level="error")
            return False
    
    def calculate_factor(self, factor_id: str, start_date: str, end_date: str,
                        stock_list: List[str] = None) -> Dict[str, Any]:
        """
        计算因子（核心方法）
        
        Args:
            factor_id: 因子ID
            start_date: 开始日期（YYYYMMDD）
            end_date: 结束日期（YYYYMMDD）
            stock_list: 股票列表（可选，不指定则计算全市场）
        
        Returns:
            计算结果统计
        """
        try:
            # 获取因子元数据
            metadata = self.get_factor_metadata(factor_id)
            if not metadata:
                return {"success": False, "message": f"因子不存在: {factor_id}"}
            
            factor_info = metadata[0]
            
            # 创建计算日志
            log_id = self._create_calculation_log(factor_id, start_date, end_date)
            
            # 更新因子状态为计算中
            self._update_factor_status(factor_id, "calculating")
            
            # 动态加载因子计算类
            calculation_class = factor_info['calculation_class']
            params = json.loads(factor_info['params']) if factor_info['params'] else {}
            factor_instance = self._load_factor_class(calculation_class, factor_id, params)

            if not factor_instance:
                self._update_calculation_log(log_id, "failed", error="无法加载因子类")
                return {"success": False, "message": "无法加载因子计算类"}

            # 确保因子列在数据库中存在
            if not self._ensure_factor_columns(factor_id, factor_instance):
                self._update_calculation_log(log_id, "failed", error="无法创建因子列")
                return {"success": False, "message": "无法创建因子列"}
            
            # 获取股票列表
            if not stock_list:
                stock_list = self._get_all_stocks()
            
            # 批量计算
            start_time = datetime.now()
            success_count = 0
            failed_count = 0
            total_count = len(stock_list)
            
            self._safe_log(f"开始计算因子: {factor_id}, 股票数: {total_count}, 日期: {start_date} ~ {end_date}")
            
            for idx, symbol in enumerate(stock_list):
                try:
                    # 计算单个股票的因子
                    factor_df = factor_instance.calculate(symbol, start_date, end_date)
                    
                    if factor_df is not None and not factor_df.empty:
                        # 保存到数据库
                        self._save_factor_data(factor_df, factor_instance.get_factor_columns())
                        success_count += len(factor_df)
                    
                    # 进度日志（每100只股票打印一次）
                    if (idx + 1) % 100 == 0:
                        self._safe_log(f"进度: {idx + 1}/{total_count} ({(idx + 1) / total_count * 100:.1f}%)")
                        
                except Exception as e:
                    self._safe_log(f"计算因子失败 {symbol}: {str(e)}", level="error")
                    failed_count += 1
                    continue
            
            # 计算耗时
            duration = (datetime.now() - start_time).total_seconds()
            
            # 更新计算日志
            self._update_calculation_log(
                log_id, "completed", 
                duration=duration,
                processed=total_count,
                success=success_count,
                failed=failed_count
            )
            
            # 更新因子元数据
            self._update_factor_metadata(factor_id, start_date, end_date, duration, success_count)
            
            self._safe_log(f"因子计算完成: {factor_id}, 成功: {success_count}, 失败: {failed_count}, 耗时: {duration:.2f}秒")
            
            return {
                "success": True,
                "factor_id": factor_id,
                "total_stocks": total_count,
                "success_records": success_count,
                "failed_records": failed_count,
                "duration": duration
            }
            
        except Exception as e:
            self._safe_log(f"计算因子异常: {str(e)}", level="error")
            if 'log_id' in locals():
                self._update_calculation_log(log_id, "failed", error=str(e))
            self._update_factor_status(factor_id, "error")
            return {"success": False, "message": str(e)}
    
    def _create_calculation_log(self, factor_id: str, start_date: str, end_date: str) -> int:
        """创建计算日志记录"""
        conn = sqlite3.connect(self.sqlite_path)
        cursor = conn.cursor()
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO factor_calculation_log 
            (factor_id, calculation_type, start_date, end_date, status, start_time, created_at)
            VALUES (?, 'full', ?, ?, 'running', ?, ?)
        """, (factor_id, start_date, end_date, now, now))
        
        log_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return log_id
    
    def _update_calculation_log(self, log_id: int, status: str, duration: float = None,
                               processed: int = 0, success: int = 0, failed: int = 0,
                               error: str = None):
        """更新计算日志"""
        conn = sqlite3.connect(self.sqlite_path)
        cursor = conn.cursor()
        
        end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute("""
            UPDATE factor_calculation_log 
            SET status = ?, end_time = ?, duration = ?, 
                processed_records = ?, success_records = ?, failed_records = ?,
                error_message = ?
            WHERE log_id = ?
        """, (status, end_time, duration, processed, success, failed, error, log_id))
        
        conn.commit()
        conn.close()
    
    def _update_factor_status(self, factor_id: str, status: str):
        """更新因子状态"""
        conn = sqlite3.connect(self.sqlite_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE factor_metadata 
            SET status = ?, updated_at = ?
            WHERE factor_id = ?
        """, (status, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), factor_id))
        
        conn.commit()
        conn.close()
    
    def _update_factor_metadata(self, factor_id: str, start_date: str, end_date: str,
                               duration: float, total_records: int):
        """更新因子元数据"""
        conn = sqlite3.connect(self.sqlite_path)
        cursor = conn.cursor()
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute("""
            UPDATE factor_metadata 
            SET status = 'active',
                coverage_start_date = ?,
                coverage_end_date = ?,
                last_calculation_time = ?,
                calculation_duration = ?,
                total_records = ?,
                updated_at = ?
            WHERE factor_id = ?
        """, (start_date, end_date, now, duration, total_records, now, factor_id))
        
        conn.commit()
        conn.close()
    
    def _load_factor_class(self, calculation_class: str, factor_id: str, params: Dict):
        """动态加载因子计算类"""
        try:
            # 例如: "panda_backtest.factor.factors.resistance_factor.ResistanceFactor"
            module_path, class_name = calculation_class.rsplit('.', 1)
            module = importlib.import_module(module_path)
            factor_class = getattr(module, class_name)
            return factor_class(factor_id, params)
        except Exception as e:
            self._safe_log(f"加载因子类失败 {calculation_class}: {str(e)}", level="error")
            return None
    
    def _get_all_stocks(self) -> List[str]:
        """获取全市场股票列表"""
        try:
            db_handler = DatabaseHandler(config=config)
            stocks = db_handler.mongo_find(
                db_name=config["MONGO_DB"],
                collection_name="stock_info_new",
                query={"type": 0},
                projection={"_id": 0, "symbol": 1}
            )
            stock_list = [s['symbol'] for s in stocks if 'symbol' in s]
            # 只保留沪深A股，排除科创板和创业板
            stock_list = [
                s for s in stock_list
                if (s.endswith('.SH') and not s.startswith('688')) or
                   (s.endswith('.SZ') and not s.startswith('3'))
            ]
            return stock_list
        except Exception as e:
            self._safe_log(f"获取股票列表失败: {str(e)}", level="error")
            return []
    
    def _save_factor_data(self, factor_df, factor_columns: List[str]):
        """保存因子数据到SQLite（使用UPSERT）"""
        try:
            import pandas as pd
            conn = sqlite3.connect(self.sqlite_path)
            
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            factor_df['created_at'] = now
            
            # 构建动态SQL
            columns = ['symbol', 'date'] + factor_columns + ['created_at']
            
            for _, row in factor_df.iterrows():
                # 先尝试更新
                update_cols = [col for col in columns if col not in ['symbol', 'date']]
                update_clause = ", ".join([f"{col} = ?" for col in update_cols])
                values_update = [row.get(col) for col in update_cols] + [row['symbol'], row['date']]
                
                cursor = conn.cursor()
                cursor.execute(f"""
                    UPDATE factor_data 
                    SET {update_clause}
                    WHERE symbol = ? AND date = ?
                """, values_update)
                
                # 如果没有更新（行不存在），则插入
                if cursor.rowcount == 0:
                    placeholders = ', '.join(['?' for _ in columns])
                    values_insert = [row.get(col) for col in columns]
                    cursor.execute(f"""
                        INSERT INTO factor_data ({', '.join(columns)})
                        VALUES ({placeholders})
                    """, values_insert)
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self._safe_log(f"保存因子数据失败: {str(e)}", level="error")
            raise
    
    def get_calculation_logs(self, factor_id: str = None, limit: int = 50) -> List[Dict]:
        """获取计算日志"""
        try:
            conn = sqlite3.connect(self.sqlite_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if factor_id:
                cursor.execute("""
                    SELECT * FROM factor_calculation_log 
                    WHERE factor_id = ? 
                    ORDER BY created_at DESC 
                    LIMIT ?
                """, (factor_id, limit))
            else:
                cursor.execute("""
                    SELECT * FROM factor_calculation_log 
                    ORDER BY created_at DESC 
                    LIMIT ?
                """, (limit,))
            
            rows = cursor.fetchall()
            conn.close()
            
            return [dict(row) for row in rows]
            
        except Exception as e:
            self._safe_log(f"获取计算日志失败: {str(e)}", level="error")
            return []

