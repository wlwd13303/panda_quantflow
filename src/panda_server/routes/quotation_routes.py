"""
行情数据API路由
提供本地MongoDB数据，替代外部API
"""
import logging
import traceback
from typing import Optional
from fastapi import APIRouter, Query, HTTPException
from datetime import datetime

from panda_server.logic.quotation.quotation_data_logic import quotation_logic
from panda_server.models.quotation.query_quotation_response import (
    QueryLiveDataResponse,
    QuotationBarData
)

logger = logging.getLogger(__name__)

# 创建路由实例
router = APIRouter(
    prefix="/instrument",
    tags=["quotation"]
)


@router.get("/queryLiveData", response_model=QueryLiveDataResponse)
async def query_live_data(
    quotation: str = Query(..., description="股票代码，如 000009.SZ"),
    quotationType: str = Query("stock", description="行情类型：stock/future/index"),
    period: str = Query("1m", description="K线周期：1m/5m/15m/30m/1h/1d"),
    startDate: Optional[str] = Query(None, description="开始日期 YYYYMMDD"),
    endDate: Optional[str] = Query(None, description="结束日期 YYYYMMDD"),
    limit: int = Query(500, description="返回数据条数限制", ge=1, le=5000)
) -> QueryLiveDataResponse:
    """
    查询实时行情数据（本地MongoDB）
    
    替代外部API: http://api.pandaai.online/instrument/queryLiveData
    
    示例:
    - /instrument/queryLiveData?quotation=000009.SZ&quotationType=stock&period=1m
    - /instrument/queryLiveData?quotation=600000.SH&quotationType=stock&period=1d&startDate=20251020&endDate=20251027
    """
    try:
        logger.info(
            f"查询行情数据请求: quotation={quotation}, type={quotationType}, "
            f"period={period}, startDate={startDate}, endDate={endDate}"
        )
        
        # 调用业务逻辑查询数据
        data = quotation_logic.get_live_data(
            quotation=quotation,
            quotation_type=quotationType,
            period=period,
            start_date=startDate,
            end_date=endDate,
            limit=limit
        )
        
        # 转换为响应模型
        bar_data_list = []
        for item in data:
            try:
                bar_data_list.append(QuotationBarData(**item))
            except Exception as e:
                logger.warning(f"数据转换失败: {item}, error: {e}")
                continue
        
        # 构造响应
        response = QueryLiveDataResponse(
            code="200",
            message="success",
            data=bar_data_list,
            timestamp=int(datetime.now().timestamp() * 1000)
        )
        
        logger.info(f"成功返回 {len(bar_data_list)} 条数据")
        return response
        
    except ValueError as e:
        logger.error(f"参数错误: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"查询行情数据失败: {e}\n{traceback.format_exc()}")
        return QueryLiveDataResponse(
            code="500",
            message=f"查询失败: {str(e)}",
            data=[],
            timestamp=int(datetime.now().timestamp() * 1000)
        )


@router.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "ok",
        "service": "quotation",
        "message": "本地行情数据服务正常运行"
    }

