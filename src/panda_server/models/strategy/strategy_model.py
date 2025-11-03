"""策略模型定义"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from bson import ObjectId


class StrategyModel(BaseModel):
    """策略数据模型"""
    id: Optional[str] = Field(None, alias="_id")
    name: str = Field(..., description="策略名称")
    code: str = Field(..., description="策略代码")
    description: Optional[str] = Field("", description="策略描述")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    user_id: Optional[str] = Field(None, description="用户ID")
    
    class Config:
        populate_by_name = True
        json_encoders = {
            ObjectId: str,
            datetime: lambda v: v.isoformat()
        }


class CreateStrategyRequest(BaseModel):
    """创建策略请求"""
    name: str = Field(..., description="策略名称")
    code: str = Field(..., description="策略代码")
    description: Optional[str] = Field("", description="策略描述")


class UpdateStrategyRequest(BaseModel):
    """更新策略请求"""
    name: Optional[str] = Field(None, description="策略名称")
    code: Optional[str] = Field(None, description="策略代码")
    description: Optional[str] = Field(None, description="策略描述")


class StrategyResponse(BaseModel):
    """策略响应"""
    success: bool = True
    message: str = "操作成功"
    data: Optional[StrategyModel] = None


class StrategyListResponse(BaseModel):
    """策略列表响应"""
    success: bool = True
    message: str = "操作成功"
    data: list[StrategyModel] = []
    total: int = 0

