import logging
from fastapi import HTTPException, status
from panda_server.dao.backtest_dao import BacktestPositionDAO
from common.backtest.model.backtest_position import BacktestPositionModel
from panda_server.models.backtest.query_position_response import QueryBacktestPositionListResponse, QueryBacktestPositionListResponseData
from typing import Optional

logger = logging.getLogger(__name__)


async def backtest_position_get_logic(
    back_id: str,
    page: int = 1,
    page_size: int = 10,
    date: Optional[str] = None
) -> QueryBacktestPositionListResponse:
    """
    根据回测ID分页获取回测持仓信息，并做模型校验，返回统一结构
    支持可选日期过滤
    """
    # 格式化日期
    formatted_date = None
    if date:
        try:
            formatted_date = date.replace("-", "")
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format, please use YYYY-MM-DD format",
            )
    
    # 使用 SQLite DAO 获取持仓数据
    data_list, total_count = await BacktestPositionDAO.list_by_back_id(back_id, page, page_size, formatted_date)
    
    validated_items = []
    for data in data_list:
        try:
            validated = BacktestPositionModel.model_validate(data)
            validated_items.append(validated)
        except Exception as e:
            logger.warning(f"Position data validation failed: {e}, raw: {data}")
    
    pagination = {
        "total": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": (total_count + page_size - 1) // page_size
    }
    response_data = QueryBacktestPositionListResponseData(items=validated_items, pagination=pagination)
    return QueryBacktestPositionListResponse(data=response_data) 