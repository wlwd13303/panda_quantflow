import logging
from fastapi import HTTPException, status
from panda_server.dao.backtest_dao import BacktestLogDAO
from common.backtest.model.backtest_user_strategy_log import BacktestUserStrategyLogModel
from panda_server.models.backtest.query_user_strategy_log_response import QueryBacktestUserStrategyLogListResponse, QueryBacktestUserStrategyLogListResponseData

logger = logging.getLogger(__name__)


async def backtest_user_strategy_log_get_logic(
    relation_id: str,
    last_sort: int = None,
    limit: int = 20
) -> QueryBacktestUserStrategyLogListResponse:
    """
    根据 relation_id 获取 panda_user_strategy_log 记录，支持基于 sort 字段的游标式分页，并返回游标信息
    """
    if not relation_id or not isinstance(relation_id, str) or len(relation_id) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid relation_id",
        )
    
    # 使用 SQLite DAO 获取日志数据
    data_list = await BacktestLogDAO.list_by_relation_id(relation_id, last_sort, limit)
    
    validated_items = []
    for data in data_list:
        try:
            validated = BacktestUserStrategyLogModel.model_validate(data)
            validated_items.append(validated)
        except Exception as e:
            logger.warning(f"User strategy log data validation failed: {e}, raw: {data}")
    
    current = data_list[-1]["sort"] if data_list else None
    cursor_info = {
        "current": current,
        "limit": limit
    }
    response_data = QueryBacktestUserStrategyLogListResponseData(items=validated_items, cursor=cursor_info)
    return QueryBacktestUserStrategyLogListResponse(data=response_data) 