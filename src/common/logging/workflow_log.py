from datetime import datetime
import logging
from typing import Optional, Any
from pydantic import Field
from bson import ObjectId
import asyncio

from .user_log import UserLog
from panda_server.config.database import mongodb

class WorkflowLog(UserLog):
    """
    工作流日志数据模型，继承自UserLog
    
    额外字段说明：
    - workflow_run_id: 工作流运行ID（可选）
    - work_node_id: 工作节点ID（可选）
    - sequence: 日志在同一workflow中的序列号，用于排序和分页
    - workflow_id: 工作流ID
    """
    workflow_run_id: Optional[str] = None
    work_node_id: Optional[str] = None
    sequence: int = Field(default=0, description="日志在同一workflow中的序列号，从1开始自增，0表示待自动分配")
    workflow_id: Optional[str] = None
    type: str = "workflow_run"  # 覆盖父类的默认值

class WorkflowLogRepository:
    """工作流日志仓库类"""
    def __init__(self, db):
        self.collection = db["workflow_logs"]
    
    async def get_next_sequence(self, workflow_run_id: str) -> int:
        """获取指定workflow的下一个序列号（使用原子操作确保并发安全）"""
        # 使用 findOneAndUpdate 原子操作来获取并递增序列号（直接 upsert）
        counter_collection = self.collection.database["workflow_sequence_counters"]
        result = await counter_collection.find_one_and_update(
            {"workflow_run_id": workflow_run_id},
            {"$inc": {"sequence": 1}},  # 原子递增，第一次会从0变成1
            upsert=True,
            return_document=True  # 返回更新后的文档
        )
        return result["sequence"]
    
    async def insert_workflow_log(self, workflow_log: WorkflowLog):
        """插入一条工作流日志"""
        # 如果有workflow_run_id且sequence为0，自动生成序列号
        if workflow_log.workflow_run_id and workflow_log.sequence == 0:
            workflow_log.sequence = await self.get_next_sequence(workflow_log.workflow_run_id)
        
        return await self.collection.insert_one(workflow_log.dict(by_alias=True))
    
    async def get_workflow_logs_by_filters(
        self,
        user_id: str,
        workflow_run_id: Optional[str] = None,
        work_node_id: Optional[str] = None,
        log_level: Optional[str] = None,
        last_sequence: Optional[int] = None,
        limit: int = 5
    ):
        """根据筛选条件获取工作流日志（基于sequence分页）"""
        query = {"user_id": user_id}
        
        # 添加可选筛选条件
        if workflow_run_id:
            query["workflow_run_id"] = workflow_run_id
        if work_node_id:
            query["work_node_id"] = work_node_id
        if log_level:
            query["level"] = log_level
        
        # 分页逻辑：基于sequence字段
        if last_sequence is not None:
            # 从指定序列号开始（包含该序列号）：获取序列号大于等于last_sequence的日志
            query["sequence"] = {"$gte": last_sequence}
        
        # 排序逻辑：如果有workflow_run_id，按sequence排序；否则按timestamp排序
        if workflow_run_id:
            # 同一个workflow内，按sequence升序排序确保日志顺序正确
            sort_criteria = [("sequence", 1)]
        else:
            # 跨workflow查询时，按时间戳排序，同时考虑sequence作为次要排序
            sort_criteria = [("timestamp", 1), ("sequence", 1)]
        
        cursor = self.collection.find(
            query,
            sort=sort_criteria,
            limit=limit
        )
        
        return await cursor.to_list(length=limit)
    
    async def get_workflow_logs_by_filters_legacy(
        self,
        user_id: str,
        workflow_run_id: Optional[str] = None,
        work_node_id: Optional[str] = None,
        log_level: Optional[str] = None,
        last_log_id: Optional[str] = None,
        limit: int = 5
    ):
        """根据筛选条件获取工作流日志（兼容原有的基于ObjectId分页）"""
        query = {"user_id": user_id}
        
        # 添加可选筛选条件
        if workflow_run_id:
            query["workflow_run_id"] = workflow_run_id
        if work_node_id:
            query["work_node_id"] = work_node_id
        if log_level:
            query["level"] = log_level
        
        # 分页逻辑：配合前端升序显示
        if last_log_id:
            # 向后分页：获取比 last_log_id 更新的日志
            query["_id"] = {"$gt": ObjectId(last_log_id)}
        
        cursor = self.collection.find(
            query,
            sort=[("_id", 1)],  # 按 ID 升序排序（从旧到新），配合前端升序显示
            limit=limit
        )
        
        return await cursor.to_list(length=limit)
    
    async def get_recent_workflow_logs(self, user_id: str, workflow_run_id: Optional[str] = None, limit: int = 5):
        """获取工作流最近的日志"""
        query = {"user_id": user_id}
        
        if workflow_run_id:
            query["workflow_run_id"] = workflow_run_id
            # 同一个workflow内，按sequence降序排序获取最新日志
            sort_criteria = [("sequence", -1)]
        else:
            # 跨workflow查询时，按时间戳降序排序获取最新日志
            sort_criteria = [("timestamp", -1), ("sequence", -1)]
        
        cursor = self.collection.find(
            query,
            sort=sort_criteria,
            limit=limit
        )
        return await cursor.to_list(length=limit)

class WorkflowLogger:
    """工作流日志记录器"""
    
    def __init__(self, user_id: str, workflow_run_id: Optional[str] = None, work_node_id: Optional[str] = None):
        self.user_id = user_id
        self.workflow_run_id = workflow_run_id
        self.work_node_id = work_node_id
        self.repository = None  # 延迟初始化
        self.sys_logger = logging.getLogger(__name__)
    
    def _get_repository(self):
        """获取仓库实例，支持延迟初始化"""
        if self.repository is None:
            try:
                if mongodb.db is not None:
                    self.repository = WorkflowLogRepository(mongodb.db)
                else:
                    # 数据库未连接，记录警告但不抛出异常
                    self.sys_logger.warning("MongoDB not connected, workflow logs will not be stored")
                    return None
            except Exception as e:
                self.sys_logger.error(f"Failed to create WorkflowLogRepository: {e}")
                return None
        return self.repository
    
    async def _log(self, level: str, message: str, workflow_id: Optional[str] = None, work_node_id: Optional[str] = None, **kwargs):
        """内部日志记录方法"""
        repository = self._get_repository()
        if repository is None:
            # 数据库不可用，只记录到系统日志
            self.sys_logger.info(f"[WORKFLOW_LOG] {level} - {message} (workflow_id: {workflow_id}, work_node_id: {work_node_id}, kwargs: {kwargs})")
            return
        workflow_log = WorkflowLog(
            user_id=self.user_id,
            workflow_run_id=self.workflow_run_id,
            work_node_id=work_node_id if work_node_id is not None else self.work_node_id,
            level=level,
            message=message,
            type="workflow_run",
            workflow_id=workflow_id
        )
        # 异步插入日志
        try:
            await repository.insert_workflow_log(workflow_log)
        except Exception as e:
            # 日志记录失败不应该影响主流程，记录到系统日志
            self.sys_logger.error(f"Failed to insert workflow log: {e}")
    
    def _sync_log(self, level: str, message: str, workflow_id: Optional[str] = None, work_node_id: Optional[str] = None, **kwargs):
        """同步日志记录（在异步上下文中使用）"""
        try:
            # 获取当前事件循环
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self._log(level, message, workflow_id, work_node_id, **kwargs))
            else:
                loop.run_until_complete(self._log(level, message, workflow_id, work_node_id, **kwargs))
        except RuntimeError:
            try:
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                new_loop.run_until_complete(self._log(level, message, workflow_id, work_node_id, **kwargs))
            except Exception as e:
                self.sys_logger.error(f"Failed to log workflow message in new loop: {e}")
            finally:
                try:
                    new_loop.close()
                except Exception:
                    pass
        except Exception as e:
            self.sys_logger.error(f"Failed to sync log: {e}")
    
    def debug(self, message: str, workflow_id: Optional[str] = None, work_node_id: Optional[str] = None, **kwargs):
        self._sync_log("DEBUG", message, workflow_id, work_node_id, **kwargs)
    
    def info(self, message: str, workflow_id: Optional[str] = None, work_node_id: Optional[str] = None, **kwargs):
        self._sync_log("INFO", message, workflow_id, work_node_id, **kwargs)
    
    def warning(self, message: str, workflow_id: Optional[str] = None, work_node_id: Optional[str] = None, **kwargs):
        self._sync_log("WARNING", message, workflow_id, work_node_id, **kwargs)
    
    def error(self, message: str, workflow_id: Optional[str] = None, work_node_id: Optional[str] = None, **kwargs):
        self._sync_log("ERROR", message, workflow_id, work_node_id, **kwargs)
    
    def critical(self, message: str, workflow_id: Optional[str] = None, work_node_id: Optional[str] = None, **kwargs):
        self._sync_log("CRITICAL", message, workflow_id, work_node_id, **kwargs)

# 注意：UserLogger 现在位于 user_log.py 中，专门用于通用用户日志 