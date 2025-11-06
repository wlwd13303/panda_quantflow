"""策略数据访问层（DAO）
使用 SQLite 存储策略数据
"""
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from panda_server.config.sqlite_database import sqlite_db

logger = logging.getLogger(__name__)


class StrategyDAO:
    """策略数据访问对象"""
    
    @staticmethod
    async def create(name: str, code: str, description: str = "", user_id: str = None) -> Dict[str, Any]:
        """创建策略"""
        try:
            async with sqlite_db.get_connection() as conn:
                cursor = await conn.execute(
                    """
                    INSERT INTO panda_strategy (name, code, description, user_id, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (name, code, description, user_id, datetime.now(), datetime.now())
                )
                await conn.commit()
                strategy_id = cursor.lastrowid
                
                # 获取刚创建的策略
                return await StrategyDAO.get_by_id(strategy_id)
        except Exception as e:
            logger.error(f"创建策略失败: {e}")
            raise
    
    @staticmethod
    async def get_by_id(strategy_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取策略"""
        try:
            async with sqlite_db.get_connection() as conn:
                cursor = await conn.execute(
                    """
                    SELECT id as _id, name, code, description, user_id, created_at, updated_at
                    FROM panda_strategy
                    WHERE id = ?
                    """,
                    (strategy_id,)
                )
                row = await cursor.fetchone()
                if row:
                    result = dict(row)
                    # 将 _id 转换为字符串，以符合 StrategyModel 的要求
                    result["_id"] = str(result["_id"])
                    return result
                return None
        except Exception as e:
            logger.error(f"获取策略失败: {e}")
            raise
    
    @staticmethod
    async def list_all(page: int = 1, page_size: int = 20) -> tuple[List[Dict[str, Any]], int]:
        """获取策略列表
        
        Returns:
            (strategies, total): 策略列表和总数
        """
        try:
            async with sqlite_db.get_connection() as conn:
                # 获取总数
                cursor = await conn.execute("SELECT COUNT(*) FROM panda_strategy")
                row = await cursor.fetchone()
                total = row[0] if row else 0
                
                # 获取分页数据，并关联回测统计信息
                offset = (page - 1) * page_size
                cursor = await conn.execute(
                    """
                    SELECT 
                        s.id as _id, 
                        s.name, 
                        s.code, 
                        s.description, 
                        s.user_id, 
                        s.created_at, 
                        s.updated_at,
                        COALESCE(COUNT(DISTINCT CASE WHEN b.strategy_id IS NOT NULL THEN b.run_id END), 0) as backtest_count,
                        MAX(b.created_at) as last_backtest_time
                    FROM panda_strategy s
                    LEFT JOIN panda_back_test b ON CAST(s.id AS TEXT) = b.strategy_id AND b.strategy_id IS NOT NULL
                    GROUP BY s.id, s.name, s.code, s.description, s.user_id, s.created_at, s.updated_at
                    ORDER BY s.updated_at DESC
                    LIMIT ? OFFSET ?
                    """,
                    (page_size, offset)
                )
                rows = await cursor.fetchall()
                strategies = []
                for row in rows:
                    strategy_dict = dict(row)
                    # 将 _id 转换为字符串，以符合 StrategyModel 的要求
                    strategy_dict["_id"] = str(strategy_dict["_id"])
                    strategies.append(strategy_dict)
                
                return strategies, total
        except Exception as e:
            logger.error(f"获取策略列表失败: {e}")
            raise
    
    @staticmethod
    async def update(strategy_id: int, name: str = None, code: str = None, 
                    description: str = None) -> Optional[Dict[str, Any]]:
        """更新策略"""
        try:
            async with sqlite_db.get_connection() as conn:
                # 构建更新字段
                update_fields = ["updated_at = ?"]
                params = [datetime.now()]
                
                if name is not None:
                    update_fields.append("name = ?")
                    params.append(name)
                if code is not None:
                    update_fields.append("code = ?")
                    params.append(code)
                if description is not None:
                    update_fields.append("description = ?")
                    params.append(description)
                
                params.append(strategy_id)
                
                await conn.execute(
                    f"""
                    UPDATE panda_strategy
                    SET {', '.join(update_fields)}
                    WHERE id = ?
                    """,
                    params
                )
                await conn.commit()
                
                # 返回更新后的策略
                return await StrategyDAO.get_by_id(strategy_id)
        except Exception as e:
            logger.error(f"更新策略失败: {e}")
            raise
    
    @staticmethod
    async def delete(strategy_id: int) -> bool:
        """删除策略"""
        try:
            async with sqlite_db.get_connection() as conn:
                cursor = await conn.execute(
                    "DELETE FROM panda_strategy WHERE id = ?",
                    (strategy_id,)
                )
                await conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"删除策略失败: {e}")
            raise


