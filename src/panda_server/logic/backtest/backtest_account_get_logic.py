import logging
from fastapi import HTTPException, status
from panda_server.dao.backtest_dao import BacktestAccountDAO
from common.backtest.model.backtest_account import BacktestAccountModel
from panda_server.models.backtest.query_account_response import QueryBacktestAccountListResponse, QueryBacktestAccountListResponseData

logger = logging.getLogger(__name__)


async def backtest_account_get_logic(
    back_id: str,
    page: int = 1,
    page_size: int = 10
) -> QueryBacktestAccountListResponse:
    """
    根据回测ID分页获取回测账户信息，并做模型校验，返回统一结构
    """
    # 使用 SQLite DAO 获取账户数据
    data_list, total_count = await BacktestAccountDAO.list_by_back_id(back_id, page, page_size)
    
    validated_items = []
    for data in data_list:
        try:
            validated = BacktestAccountModel.model_validate(data)
            validated_items.append(validated)
        except Exception as e:
            logger.warning(f"Account data validation failed: {e}, raw: {data}")
            # 失败时可选：跳过或原样返回dict
            # validated_items.append(data)
    
    pagination = {
        "total": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": (total_count + page_size - 1) // page_size
    }
    response_data = QueryBacktestAccountListResponseData(items=validated_items, pagination=pagination)
    return QueryBacktestAccountListResponse(data=response_data) 