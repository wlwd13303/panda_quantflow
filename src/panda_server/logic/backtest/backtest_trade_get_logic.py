import logging
from fastapi import HTTPException, status
from panda_server.dao.backtest_dao import BacktestTradeDAO
from common.backtest.model.backtest_trade import BacktestTradeModel
from panda_server.models.backtest.query_trade_response import QueryBacktestTradeListResponse, QueryBacktestTradeListResponseData

logger = logging.getLogger(__name__)


async def backtest_trade_get_logic(
    back_id: str,
    page: int = 1,
    page_size: int = 10
) -> QueryBacktestTradeListResponse:
    """
    根据回测ID分页获取回测交易信息，并做模型校验，返回统一结构
    """
    # 使用 SQLite DAO 获取交易数据
    data_list, total_count = await BacktestTradeDAO.list_by_back_id(back_id, page, page_size)
    
    validated_items = []
    for data in data_list:
        try:
            validated = BacktestTradeModel.model_validate(data)
            validated_items.append(validated)
        except Exception as e:
            logger.warning(f"Trade data validation failed: {e}, raw: {data}")
    
    pagination = {
        "total": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": (total_count + page_size - 1) // page_size
    }
    response_data = QueryBacktestTradeListResponseData(items=validated_items, pagination=pagination)
    return QueryBacktestTradeListResponse(data=response_data) 