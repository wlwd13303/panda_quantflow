from pydantic import BaseModel, Field
from typing import Optional
from ..enums.role_type import RoleType


class CreateNewMessageRequest(BaseModel):
    """
    Create New Message Request
    创建新消息的请求模型，包含 role、content 和可选的 session_id 字段
    """
    
    role: RoleType = Field(description="消息角色")
    content: str = Field(description="消息内容")
    session_id: Optional[str] = Field(default=None, description="会话ID，可选")

    class Config:
        extra = "forbid"  # 只允许传入定义的字段
        json_schema_extra = {
            "description": "用户新消息请求模型",
            "examples": [
                {
                    "role": "user",
                    "content": "你好，请帮我解答一个问题"
                },
                {
                    "role": "user", 
                    "content": "继续之前的对话",
                    "session_id": "chat_session_123"
                }
            ]
        } 