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
from panda_server.logic.quotation.quotation_cache import quotation_cache
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
    """
    try:
        logger.info(
            f"查询行情数据请求: quotation={quotation}, type={quotationType}, "
            f"period={period}, startDate={startDate}, endDate={endDate}, limit={limit}"
        )
        
        # 调用业务逻辑查询数据
        try:
            data = quotation_logic.get_live_data(
                quotation=quotation,
                quotation_type=quotationType,
                period=period,
                start_date=startDate,
                end_date=endDate,
                limit=limit
            )
            logger.info(f"业务逻辑返回数据数量: {len(data) if data else 0}")
        except Exception as logic_error:
            logger.error(f"业务逻辑调用异常: {logic_error}\n{traceback.format_exc()}")
            raise
        
        # 转换为响应模型
        bar_data_list = []
        conversion_errors = 0
        for item in data:
            try:
                bar_data_list.append(QuotationBarData(**item))
            except Exception as e:
                conversion_errors += 1
                logger.warning(f"数据转换失败 ({conversion_errors}): {item.get('symbol', 'N/A')}, {item.get('date', 'N/A')}, error: {e}")
                continue
        
        if conversion_errors > 0:
            logger.warning(f"数据转换失败总数: {conversion_errors}, 成功转换: {len(bar_data_list)}")
        
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


@router.get("/debug/test-query")
async def debug_test_query():
    """调试端点：测试数据库查询"""
    try:
        from common.connector.mongodb_handler import DatabaseHandler
        from common.config.config import config
        
        db_handler = DatabaseHandler(config=config)
        db_name = config["MONGO_DB"]


        # 直接查询
        result = db_handler.mongo_find(
            db_name=db_name,
            collection_name="index_market",
            query={"symbol": "000001.SH", "date": {"$gte": "20250501", "$lte": "20251001"}},
            projection={'_id': 0},
            sort=[('date', -1)]
        )
        
        # 通过业务逻辑查询
        logic_result = quotation_logic.get_live_data(
            quotation="000001.SH",
            quotation_type="index",
            period="1d",
            start_date="20250501",
            end_date="20251001",
            limit=5000
        )
        
        return {
            "db_name": db_name,
            "direct_query_count": len(result) if result else 0,
            "logic_query_count": len(logic_result) if logic_result else 0,
            "direct_query_sample": result[:3] if result else [],
            "logic_query_sample": logic_result[:3] if logic_result else []
        }
    except Exception as e:
        logger.error(f"调试查询失败: {e}\n{traceback.format_exc()}")
        return {
            "error": str(e),
            "traceback": traceback.format_exc()
        }


@router.get("/cache/stats")
async def get_cache_stats():
    """获取缓存统计信息"""
    try:
        stats = quotation_cache.get_stats()
        return {
            "success": True,
            "data": stats,
            "message": "缓存统计信息获取成功"
        }
    except Exception as e:
        logger.error(f"获取缓存统计失败: {e}")
        return {
            "success": False,
            "message": f"获取缓存统计失败: {str(e)}"
        }


@router.post("/cache/clear")
async def clear_cache():
    """清空缓存"""
    try:
        quotation_cache.clear()
        return {
            "success": True,
            "message": "缓存已清空"
        }
    except Exception as e:
        logger.error(f"清空缓存失败: {e}")
        return {
            "success": False,
            "message": f"清空缓存失败: {str(e)}"
        }


@router.post("/cache/clean")
async def clean_expired_cache():
    """清理过期缓存"""
    try:
        count = quotation_cache.clean_expired()
        return {
            "success": True,
            "message": f"清理了 {count} 个过期缓存",
            "cleaned_count": count
        }
    except Exception as e:
        logger.error(f"清理过期缓存失败: {e}")
        return {
            "success": False,
            "message": f"清理过期缓存失败: {str(e)}"
        }

