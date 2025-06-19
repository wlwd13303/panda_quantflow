from pydantic import BaseModel, Field
import logging

from typing import Generic, TypeVar

T = TypeVar("T")

class BaseAPIResponse(BaseModel, Generic[T]):
    """
    API响应基类，统一返回格式
    
    返回数据格式如下
    {
        "code": 0,
        "message": "success",
        "data": {...}
    }
    
    其中 code 为业务逻辑状态码, 和 http status code 独立.
    统一用 0 表示成功, 其它数值表示各个业务逻辑层面的异常.
    """

    code: int = Field(default=0)
    message: str = Field(default="success")
    data: T = Field(default={})
