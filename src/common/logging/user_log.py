from datetime import datetime
import logging
from typing import Optional, Any
from pydantic import BaseModel, Field
from bson import ObjectId

# 添加 logger
logger = logging.getLogger(__name__)

class UserLog(BaseModel):
    """
    通用用户日志数据模型
    
    字段说明：
    - id: MongoDB 的 ObjectId，会自动生成
    - user_id: 用户ID
    - timestamp: 日志产生的时间戳
    - level: 日志级别（INFO, WARNING, ERROR 等）
    - message: 日志消息内容
    - type: 日志类型，默认为user_action
    """
    id: str = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    user_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    level: str = "INFO"
    message: str
    type: str = "user_action"

    class Config:
        populate_by_name = True
        json_encoders = {
            ObjectId: str
        }

# UserLog 是基础日志模型，WorkflowLog 继承自这个类
# 所有日志实际存储在 workflow_logs 集合中



# 使用示例：
"""
# UserLog 是基础日志模型，通常不直接使用，而是通过 WorkflowLog 使用
# WorkflowLog 继承自 UserLog，添加了工作流相关字段

# 创建工作流日志示例（继承了UserLog的所有字段）
from common.logging.workflow_log import WorkflowLog

workflow_log = WorkflowLog(
    user_id="user123",
    message="工作流节点执行完成", 
    level="INFO",
    type="workflow_run",
    workflow_run_id="workflow456",
    work_node_id="node789",
    workflow_id="workflow_id_123"
)
""" 