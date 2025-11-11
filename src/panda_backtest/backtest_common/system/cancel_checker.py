"""回测中断检查器"""
import logging
import sqlite3
from typing import Optional
from panda_server.config.sqlite_database import sqlite_db

logger = logging.getLogger(__name__)


class BacktestCancelledException(Exception):
    """回测被用户终止异常"""
    pass


class CancelChecker:
    """检查回测是否被用户终止的检查器"""
    
    def __init__(self, backtest_id: str):
        self.backtest_id = backtest_id
        self._check_counter = 0
        self._check_interval = 5  # 每5次循环检查一次
        
    def check_if_cancelled(self):
        """检查回测是否被终止
        
        为了性能考虑，不是每次都检查，而是间隔检查
        如果检测到终止标志，抛出 BacktestCancelledException 异常
        """
        self._check_counter += 1
        
        # 每N次循环才检查一次，避免频繁访问数据库
        if self._check_counter % self._check_interval != 0:
            return
            
        try:
            # 使用同步的 sqlite3 连接查询数据库
            if sqlite_db.db_path is None:
                logger.warning("数据库路径未设置，无法检查回测终止状态")
                return
            
            # 创建同步连接
            conn = sqlite3.connect(str(sqlite_db.db_path))
            conn.row_factory = sqlite3.Row
            
            try:
                cursor = conn.execute(
                    "SELECT status FROM panda_back_test WHERE run_id = ?",
                    (self.backtest_id,)
                )
                row = cursor.fetchone()
                
                if row:
                    status = row['status'] if hasattr(row, 'keys') else row[0]
                    logger.debug(f"回测 {self.backtest_id} 当前状态: {status}")
                    if status == 'cancelled':
                        logger.info(f"检测到回测终止标志: {self.backtest_id}")
                        raise BacktestCancelledException(f"回测 {self.backtest_id} 已被用户终止")
                else:
                    logger.warning(f"未找到回测记录: {self.backtest_id}")
            finally:
                conn.close()
                    
        except BacktestCancelledException:
            # 重新抛出终止异常
            raise
        except Exception as e:
            # 数据库查询失败，记录错误但不影响回测继续运行
            logger.warning(f"检查回测终止状态失败: {e}")
            import traceback
            logger.debug(traceback.format_exc())

