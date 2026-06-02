import logging
from typing import Optional

from fastapi import HTTPException, status

from common.backtest.model.backtest_position import BacktestPositionModel
from panda_server.dao.backtest_dao import BacktestPositionDAO, BacktestAccountDAO
from panda_server.models.backtest.query_position_response import (
    QueryBacktestPositionListResponse,
    QueryBacktestPositionListResponseData,
)

logger = logging.getLogger(__name__)


async def backtest_position_get_logic(
    back_id: str,
    page: int = 1,
    page_size: int = 10,
    date: Optional[str] = None,
) -> QueryBacktestPositionListResponse:
    """Get paginated position list and map it to response model."""
    formatted_date = None
    if date:
        try:
            formatted_date = date.replace("-", "")
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format, please use YYYY-MM-DD format",
            )

    data_list, total_count = await BacktestPositionDAO.list_by_back_id(
        back_id, page, page_size, formatted_date
    )

    dates = [item.get("date") for item in data_list if item.get("date")]
    total_value_by_date = await BacktestAccountDAO.get_total_value_by_dates(back_id, dates)

    validated_items = []
    for data in data_list:
        try:
            market_value = data.get("market_value") or 0
            total_value = total_value_by_date.get(data.get("date") or "")
            position_ratio = None
            if market_value and total_value:
                try:
                    position_ratio = float(market_value) / float(total_value)
                except Exception:
                    position_ratio = None

            dividend_received = data.get("dividend_received") or 0

            mapped_data = {
                **data,
                "contract_code": data.get("symbol"),
                "contract_name": data.get("contract_name"),
                "position": int(data.get("volume") or 0),
                "price": data.get("avg_price"),
                "last_price": data.get("market_price"),
                "gmt_create": data.get("date") or data.get("created_at"),
                "position_ratio": position_ratio,
                "dividend_received": dividend_received,
            }
            validated = BacktestPositionModel.model_validate(mapped_data)
            validated_items.append(validated)
        except Exception as e:
            logger.warning(f"Position data validation failed: {e}, raw: {data}")

    pagination = {
        "total": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": (total_count + page_size - 1) // page_size,
    }
    response_data = QueryBacktestPositionListResponseData(
        items=validated_items, pagination=pagination
    )
    return QueryBacktestPositionListResponse(data=response_data)
