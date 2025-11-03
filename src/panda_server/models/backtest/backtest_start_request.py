"""回测启动请求模型"""
from pydantic import BaseModel, Field
from typing import Optional


class BacktestStartRequest(BaseModel):
    """启动回测请求"""
    strategy_code: str = Field(..., description="策略代码内容")
    strategy_name: Optional[str] = Field("临时策略", description="策略名称")
    
    # 回测时间配置
    start_date: str = Field(..., description="回测开始日期 YYYYMMDD")
    end_date: str = Field(..., description="回测结束日期 YYYYMMDD")
    
    # 资金配置
    start_capital: float = Field(10000000, description="初始资金")
    
    # 账户配置
    account_id: str = Field("8888", description="账户ID")
    account_type: int = Field(0, description="账户类型 0-股票")
    
    # 交易费用配置
    commission_rate: float = Field(1, description="佣金费率（千分之一）")
    slippage: float = Field(0, description="滑点")
    
    # 行情配置
    frequency: str = Field("1d", description="数据频率 1d/1m")
    matching_type: int = Field(1, description="成交方式 0-收盘价 1-开盘价")
    standard_symbol: str = Field("000001.SH", description="基准指数")
    
    # 其他配置
    margin_rate: float = Field(1, description="保证金率")
    start_future_capital: float = Field(10000000, description="期货初始资金")
    start_fund_capital: float = Field(1000000, description="基金初始资金")


class BacktestStartResponse(BaseModel):
    """启动回测响应"""
    success: bool = True
    message: str = "回测已启动"
    data: dict = Field(default_factory=dict)
    back_test_id: Optional[str] = None

