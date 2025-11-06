"""回测数据访问层（DAO）
使用 SQLite 存储回测数据
"""
import logging
import json
from typing import Optional, List, Dict, Any
from datetime import datetime
from panda_server.config.sqlite_database import sqlite_db

logger = logging.getLogger(__name__)


class BacktestDAO:
    """回测数据访问对象"""
    
    @staticmethod
    async def create(run_id: str, strategy_name: str, **kwargs) -> Dict[str, Any]:
        """创建回测记录"""
        try:
            async with sqlite_db.get_connection() as conn:
                # 定义允许的字段（白名单，防止 SQL 注入）
                allowed_fields = [
                    'run_id', 'strategy_name', 'strategy_id', 'strategy_code', 'start_date', 'end_date',
                    'start_capital', 'commission_rate', 'frequency', 'standard_symbol',
                    'matching_type', 'account_id', 'account_type', 'slippage',
                    'margin_rate', 'start_future_capital', 'start_fund_capital',
                    'status', 'progress'
                ]
                
                # 构建字段和值
                fields_to_insert = ['run_id', 'strategy_name']
                values = [run_id, strategy_name]
                placeholders = ['?', '?']
                
                # 只添加存在于 kwargs 且在白名单中的字段
                for field in allowed_fields[2:]:  # 跳过 run_id 和 strategy_name
                    if field in kwargs:
                        fields_to_insert.append(field)
                        values.append(kwargs[field])
                        placeholders.append('?')
                
                # 添加时间戳字段
                fields_to_insert.extend(['created_at', 'updated_at'])
                values.extend([datetime.now(), datetime.now()])
                placeholders.extend(['?', '?'])
                
                # 使用参数化查询，字段名来自白名单，安全
                query = f"""
                    INSERT INTO panda_back_test ({', '.join(fields_to_insert)})
                    VALUES ({', '.join(placeholders)})
                """
                
                await conn.execute(query, values)
                await conn.commit()
                
                return await BacktestDAO.get_by_run_id(run_id)
        except Exception as e:
            logger.error(f"创建回测记录失败: {e}")
            raise
    
    @staticmethod
    async def get_by_run_id(run_id: str) -> Optional[Dict[str, Any]]:
        """根据run_id获取回测记录"""
        try:
            async with sqlite_db.get_connection() as conn:
                cursor = await conn.execute(
                    """
                    SELECT id as _id, run_id, strategy_name, strategy_id, strategy_code, start_date, end_date,
                           start_capital, commission_rate, frequency, standard_symbol,
                           matching_type, account_id, account_type, slippage, margin_rate,
                           start_future_capital, start_fund_capital, status, progress,
                           error_message, result, created_at, updated_at, completed_at
                    FROM panda_back_test
                    WHERE run_id = ?
                    """,
                    (run_id,)
                )
                row = await cursor.fetchone()
                if row:
                    result = dict(row)
                    # 将 _id 转换为字符串，以符合模型的要求
                    if "_id" in result:
                        result["_id"] = str(result["_id"])
                    return result
                return None
        except Exception as e:
            logger.error(f"获取回测记录失败: {e}")
            raise
    
    @staticmethod
    async def get_by_id(back_id: str) -> Optional[Dict[str, Any]]:
        """根据整数ID获取回测记录（兼容前端传入的整数ID）"""
        try:
            async with sqlite_db.get_connection() as conn:
                cursor = await conn.execute(
                    """
                    SELECT id as _id, run_id, strategy_name, strategy_id, strategy_code, start_date, end_date,
                           start_capital, commission_rate, frequency, standard_symbol,
                           matching_type, account_id, account_type, slippage, margin_rate,
                           start_future_capital, start_fund_capital, status, progress,
                           error_message, result, created_at, updated_at, completed_at
                    FROM panda_back_test
                    WHERE id = ?
                    """,
                    (int(back_id),)
                )
                row = await cursor.fetchone()
                if row:
                    result = dict(row)
                    # 将 _id 转换为字符串，以符合模型的要求
                    if "_id" in result:
                        result["_id"] = str(result["_id"])
                    return result
                return None
        except (ValueError, TypeError):
            # 如果不是整数，返回 None
            return None
        except Exception as e:
            logger.error(f"通过ID获取回测记录失败: {e}")
            raise
    
    @staticmethod
    async def list_all(page: int = 1, page_size: int = 20, status: str = None) -> tuple[List[Dict[str, Any]], int]:
        """获取回测列表
        
        Returns:
            (backtests, total): 回测列表和总数
        """
        try:
            async with sqlite_db.get_connection() as conn:
                # 构建查询条件
                where_clause = ""
                params = []
                if status:
                    where_clause = "WHERE status = ?"
                    params.append(status)
                
                # 获取总数
                cursor = await conn.execute(
                    f"SELECT COUNT(*) FROM panda_back_test {where_clause}",
                    params
                )
                row = await cursor.fetchone()
                total = row[0] if row else 0
                
                # 获取分页数据
                offset = (page - 1) * page_size
                params.extend([page_size, offset])
                
                cursor = await conn.execute(
                    f"""
                    SELECT id as _id, run_id, strategy_name, strategy_id, strategy_code, start_date, end_date,
                           start_capital, commission_rate, frequency, standard_symbol,
                           matching_type, account_id, account_type, slippage, margin_rate,
                           start_future_capital, start_fund_capital, status, progress,
                           error_message, result, created_at, updated_at, completed_at
                    FROM panda_back_test
                    {where_clause}
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                    """,
                    params
                )
                rows = await cursor.fetchall()
                backtests = []
                for row in rows:
                    backtest_dict = dict(row)
                    # 将 _id 转换为字符串，以符合模型的要求
                    if "_id" in backtest_dict:
                        backtest_dict["_id"] = str(backtest_dict["_id"])
                    backtests.append(backtest_dict)
                
                return backtests, total
        except Exception as e:
            logger.error(f"获取回测列表失败: {e}")
            raise
    
    @staticmethod
    async def update(run_id: str, **kwargs) -> Optional[Dict[str, Any]]:
        """更新回测记录"""
        try:
            async with sqlite_db.get_connection() as conn:
                # 构建更新字段
                update_fields = ["updated_at = ?"]
                params = [datetime.now()]
                
                allowed_fields = [
                    'status', 'progress', 'error_message', 'result', 'completed_at'
                ]
                
                for field in allowed_fields:
                    if field in kwargs:
                        update_fields.append(f"{field} = ?")
                        params.append(kwargs[field])
                
                params.append(run_id)
                
                await conn.execute(
                    f"""
                    UPDATE panda_back_test
                    SET {', '.join(update_fields)}
                    WHERE run_id = ?
                    """,
                    params
                )
                await conn.commit()
                
                return await BacktestDAO.get_by_run_id(run_id)
        except Exception as e:
            logger.error(f"更新回测记录失败: {e}")
            raise
    
    @staticmethod
    async def delete(run_id: str) -> bool:
        """删除回测记录及其所有相关数据"""
        try:
            async with sqlite_db.get_connection() as conn:
                # 由于设置了外键级联删除，删除主记录会自动删除相关数据
                cursor = await conn.execute(
                    "DELETE FROM panda_back_test WHERE run_id = ?",
                    (run_id,)
                )
                await conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"删除回测记录失败: {e}")
            raise
    
    @staticmethod
    async def batch_delete(run_ids: List[str]) -> int:
        """批量删除回测记录"""
        try:
            async with sqlite_db.get_connection() as conn:
                deleted_count = 0
                for run_id in run_ids:
                    cursor = await conn.execute(
                        "DELETE FROM panda_back_test WHERE run_id = ?",
                        (run_id,)
                    )
                    deleted_count += cursor.rowcount
                await conn.commit()
                return deleted_count
        except Exception as e:
            logger.error(f"批量删除回测记录失败: {e}")
            raise


class BacktestAccountDAO:
    """回测账户数据访问对象"""
    
    @staticmethod
    async def create(back_id: str, date: str, **kwargs) -> int:
        """创建账户记录"""
        try:
            async with sqlite_db.get_connection() as conn:
                cursor = await conn.execute(
                    """
                    INSERT INTO panda_backtest_account 
                    (back_id, date, available, balance, cash, market_value, total_value, position_profit)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        back_id, date,
                        kwargs.get('available'), kwargs.get('balance'),
                        kwargs.get('cash'), kwargs.get('market_value'),
                        kwargs.get('total_value'), kwargs.get('position_profit')
                    )
                )
                await conn.commit()
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"创建账户记录失败: {e}")
            raise
    
    @staticmethod
    async def count_by_back_id(back_id: str) -> int:
        """获取指定回测的账户记录总数"""
        try:
            async with sqlite_db.get_connection() as conn:
                cursor = await conn.execute(
                    "SELECT COUNT(*) FROM panda_backtest_account WHERE back_id = ?",
                    (back_id,)
                )
                row = await cursor.fetchone()
                return row[0] if row else 0
        except Exception as e:
            logger.error(f"获取账户记录数失败: {e}")
            return 0
    
    @staticmethod
    async def list_by_back_id(back_id: str, page: int = 1, page_size: int = 1000) -> tuple[List[Dict[str, Any]], int]:
        """根据back_id获取账户列表"""
        try:
            async with sqlite_db.get_connection() as conn:
                # 获取总数
                cursor = await conn.execute(
                    "SELECT COUNT(*) FROM panda_backtest_account WHERE back_id = ?",
                    (back_id,)
                )
                row = await cursor.fetchone()
                total = row[0] if row else 0
                
                # 获取分页数据
                offset = (page - 1) * page_size
                cursor = await conn.execute(
                    """
                    SELECT id as _id, back_id, date, available, balance, cash, market_value, 
                           total_value, position_profit, created_at
                    FROM panda_backtest_account
                    WHERE back_id = ?
                    ORDER BY date
                    LIMIT ? OFFSET ?
                    """,
                    (back_id, page_size, offset)
                )
                rows = await cursor.fetchall()
                accounts = []
                for row in rows:
                    account_dict = dict(row)
                    # 将 _id 转换为字符串，以符合 BacktestAccountModel 的要求
                    if "_id" in account_dict:
                        account_dict["_id"] = str(account_dict["_id"])
                    accounts.append(account_dict)
                
                return accounts, total
        except Exception as e:
            logger.error(f"获取账户列表失败: {e}")
            raise


class BacktestPositionDAO:
    """回测持仓数据访问对象"""
    
    @staticmethod
    async def create(back_id: str, date: str, symbol: str, **kwargs) -> int:
        """创建持仓记录"""
        try:
            async with sqlite_db.get_connection() as conn:
                cursor = await conn.execute(
                    """
                    INSERT INTO panda_backtest_position 
                    (back_id, date, symbol, volume, available, avg_price, market_price, 
                     market_value, profit, profit_rate)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        back_id, date, symbol,
                        kwargs.get('volume'), kwargs.get('available'),
                        kwargs.get('avg_price'), kwargs.get('market_price'),
                        kwargs.get('market_value'), kwargs.get('profit'),
                        kwargs.get('profit_rate')
                    )
                )
                await conn.commit()
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"创建持仓记录失败: {e}")
            raise
    
    @staticmethod
    async def count_by_back_id(back_id: str) -> int:
        """获取指定回测的持仓记录总数"""
        try:
            async with sqlite_db.get_connection() as conn:
                cursor = await conn.execute(
                    "SELECT COUNT(*) FROM panda_backtest_position WHERE back_id = ?",
                    (back_id,)
                )
                row = await cursor.fetchone()
                return row[0] if row else 0
        except Exception as e:
            logger.error(f"获取持仓记录数失败: {e}")
            return 0
    
    @staticmethod
    async def list_by_back_id(back_id: str, page: int = 1, page_size: int = 100, date: str = None) -> tuple[List[Dict[str, Any]], int]:
        """根据back_id获取持仓列表"""
        try:
            async with sqlite_db.get_connection() as conn:
                # 构建查询条件
                where_clause = "WHERE back_id = ?"
                params = [back_id]
                if date:
                    where_clause += " AND date = ?"
                    params.append(date)
                
                # 获取总数
                cursor = await conn.execute(
                    f"SELECT COUNT(*) FROM panda_backtest_position {where_clause}",
                    params
                )
                row = await cursor.fetchone()
                total = row[0] if row else 0
                
                # 获取分页数据
                offset = (page - 1) * page_size
                params.extend([page_size, offset])
                
                cursor = await conn.execute(
                    f"""
                    SELECT id as _id, back_id, date, symbol, volume, available, avg_price, 
                           market_price, market_value, profit, profit_rate, created_at
                    FROM panda_backtest_position
                    {where_clause}
                    ORDER BY date, symbol
                    LIMIT ? OFFSET ?
                    """,
                    params
                )
                rows = await cursor.fetchall()
                positions = []
                for row in rows:
                    position_dict = dict(row)
                    # 将 _id 转换为字符串，以符合 BacktestPositionModel 的要求
                    if "_id" in position_dict:
                        position_dict["_id"] = str(position_dict["_id"])
                    positions.append(position_dict)
                
                return positions, total
        except Exception as e:
            logger.error(f"获取持仓列表失败: {e}")
            raise


class BacktestProfitDAO:
    """回测收益数据访问对象"""
    
    @staticmethod
    async def create(back_id: str, date: str, **kwargs) -> int:
        """创建收益记录"""
        try:
            async with sqlite_db.get_connection() as conn:
                cursor = await conn.execute(
                    """
                    INSERT INTO panda_backtest_profit 
                    (back_id, date, total_value, profit, profit_rate, 
                     cumulative_profit, cumulative_profit_rate)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        back_id, date,
                        kwargs.get('total_value'), kwargs.get('profit'),
                        kwargs.get('profit_rate'), kwargs.get('cumulative_profit'),
                        kwargs.get('cumulative_profit_rate')
                    )
                )
                await conn.commit()
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"创建收益记录失败: {e}")
            raise
    
    @staticmethod
    async def count_by_back_id(back_id: str) -> int:
        """获取指定回测的收益记录总数"""
        try:
            async with sqlite_db.get_connection() as conn:
                cursor = await conn.execute(
                    "SELECT COUNT(*) FROM panda_backtest_profit WHERE back_id = ?",
                    (back_id,)
                )
                row = await cursor.fetchone()
                return row[0] if row else 0
        except Exception as e:
            logger.error(f"获取收益记录数失败: {e}")
            return 0
    
    @staticmethod
    async def list_by_back_id(back_id: str, page: int = 1, page_size: int = 1000) -> tuple[List[Dict[str, Any]], int]:
        """根据back_id获取收益列表"""
        try:
            async with sqlite_db.get_connection() as conn:
                # 获取总数
                cursor = await conn.execute(
                    "SELECT COUNT(*) FROM panda_backtest_profit WHERE back_id = ?",
                    (back_id,)
                )
                row = await cursor.fetchone()
                total = row[0] if row else 0
                
                # 获取分页数据
                offset = (page - 1) * page_size
                cursor = await conn.execute(
                    """
                    SELECT id as _id, back_id, date, total_value, profit, profit_rate,
                           cumulative_profit, cumulative_profit_rate, created_at
                    FROM panda_backtest_profit
                    WHERE back_id = ?
                    ORDER BY date
                    LIMIT ? OFFSET ?
                    """,
                    (back_id, page_size, offset)
                )
                rows = await cursor.fetchall()
                profits = []
                for row in rows:
                    profit_dict = dict(row)
                    # 将 _id 转换为字符串，以符合 BacktestProfitModel 的要求
                    if "_id" in profit_dict:
                        profit_dict["_id"] = str(profit_dict["_id"])
                    profits.append(profit_dict)
                
                return profits, total
        except Exception as e:
            logger.error(f"获取收益列表失败: {e}")
            raise


class BacktestTradeDAO:
    """回测交易数据访问对象"""
    
    @staticmethod
    async def create(back_id: str, **kwargs) -> int:
        """创建交易记录"""
        try:
            async with sqlite_db.get_connection() as conn:
                cursor = await conn.execute(
                    """
                    INSERT INTO panda_backtest_trade 
                    (back_id, date, time, symbol, direction, offset, price, volume, amount, commission)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        back_id,
                        kwargs.get('date'), kwargs.get('time'),
                        kwargs.get('symbol'), kwargs.get('direction'),
                        kwargs.get('offset'), kwargs.get('price'),
                        kwargs.get('volume'), kwargs.get('amount'),
                        kwargs.get('commission')
                    )
                )
                await conn.commit()
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"创建交易记录失败: {e}")
            raise
    
    @staticmethod
    async def count_by_back_id(back_id: str) -> int:
        """获取指定回测的交易记录总数"""
        try:
            async with sqlite_db.get_connection() as conn:
                cursor = await conn.execute(
                    "SELECT COUNT(*) FROM panda_backtest_trade WHERE back_id = ?",
                    (back_id,)
                )
                row = await cursor.fetchone()
                return row[0] if row else 0
        except Exception as e:
            logger.error(f"获取交易记录数失败: {e}")
            return 0
    
    @staticmethod
    async def list_by_back_id(back_id: str, page: int = 1, page_size: int = 50) -> tuple[List[Dict[str, Any]], int]:
        """根据back_id获取交易列表"""
        try:
            async with sqlite_db.get_connection() as conn:
                # 获取总数
                cursor = await conn.execute(
                    "SELECT COUNT(*) FROM panda_backtest_trade WHERE back_id = ?",
                    (back_id,)
                )
                row = await cursor.fetchone()
                total = row[0] if row else 0
                
                # 获取分页数据
                offset = (page - 1) * page_size
                cursor = await conn.execute(
                    """
                    SELECT id as _id, back_id, date, time, symbol, direction, offset, 
                           price, volume, amount, commission, created_at
                    FROM panda_backtest_trade
                    WHERE back_id = ?
                    ORDER BY date, time
                    LIMIT ? OFFSET ?
                    """,
                    (back_id, page_size, offset)
                )
                rows = await cursor.fetchall()
                trades = []
                for row in rows:
                    trade_dict = dict(row)
                    # 将 _id 转换为字符串，以符合 BacktestTradeModel 的要求
                    if "_id" in trade_dict:
                        trade_dict["_id"] = str(trade_dict["_id"])
                    trades.append(trade_dict)
                
                return trades, total
        except Exception as e:
            logger.error(f"获取交易列表失败: {e}")
            raise


class BacktestLogDAO:
    """回测策略日志数据访问对象"""
    
    @staticmethod
    async def create(relation_id: str, back_id: str = None, **kwargs) -> int:
        """创建日志记录"""
        try:
            async with sqlite_db.get_connection() as conn:
                cursor = await conn.execute(
                    """
                    INSERT INTO panda_user_strategy_log 
                    (relation_id, back_id, log_level, message, timestamp, sort)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        relation_id, back_id,
                        kwargs.get('log_level'), kwargs.get('message'),
                        kwargs.get('timestamp', datetime.now()),
                        kwargs.get('sort')
                    )
                )
                await conn.commit()
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"创建日志记录失败: {e}")
            raise
    
    @staticmethod
    async def list_by_relation_id(relation_id: str, last_sort: int = None, limit: int = 20) -> List[Dict[str, Any]]:
        """根据relation_id获取日志列表（游标分页）"""
        try:
            async with sqlite_db.get_connection() as conn:
                if last_sort is not None:
                    cursor = await conn.execute(
                        """
                        SELECT id, relation_id, back_id, log_level, message, timestamp, sort
                        FROM panda_user_strategy_log
                        WHERE relation_id = ? AND sort > ?
                        ORDER BY sort
                        LIMIT ?
                        """,
                        (relation_id, last_sort, limit)
                    )
                else:
                    cursor = await conn.execute(
                        """
                        SELECT id, relation_id, back_id, log_level, message, timestamp, sort
                        FROM panda_user_strategy_log
                        WHERE relation_id = ?
                        ORDER BY sort
                        LIMIT ?
                        """,
                        (relation_id, limit)
                    )
                
                rows = await cursor.fetchall()
                logs = [dict(row) for row in rows]
                
                return logs
        except Exception as e:
            logger.error(f"获取日志列表失败: {e}")
            raise


