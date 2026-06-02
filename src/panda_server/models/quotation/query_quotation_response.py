from typing import List, Optional
from pydantic import BaseModel, Field


class QuotationBarData(BaseModel):
    """K线数据模型"""
    symbol: str = Field(..., description="股票代码")
    date: Optional[str] = Field(None, description="日期 YYYYMMDD")
    trade_date: Optional[int] = Field(None, description="交易日期")
    time: Optional[int] = Field(None, description="时间 HHmm")
    open: float = Field(..., description="开盘价")
    high: float = Field(..., description="最高价")
    low: float = Field(..., description="最低价")
    close: float = Field(..., description="收盘价")
    volume: float = Field(0, description="成交量")
    amount: Optional[float] = Field(0, description="成交额")
    adj_factor: Optional[float] = Field(None, description="后复权因子（累积调整系数）")
    
    class Config:
        json_schema_extra = {
            "example": {
                "symbol": "000009.SZ",
                "trade_date": 20251027,
                "time": 931,
                "open": 10.99,
                "high": 11.05,
                "low": 10.89,
                "close": 11.01,
                "volume": 366400,
                "amount": 4029840.0
            }
        }


class QueryLiveDataResponse(BaseModel):
    """实时行情数据响应"""
    code: str = Field(default="200", description="响应码")
    message: str = Field(default="success", description="响应消息")
    data: List[QuotationBarData] = Field(default_factory=list, description="K线数据列表")
    timestamp: int = Field(..., description="时间戳")
    
    class Config:
        json_schema_extra = {
            "example": {
                "code": "200",
                "message": "success",
                "data": [],
                "timestamp": 1761556730158
            }
        }

