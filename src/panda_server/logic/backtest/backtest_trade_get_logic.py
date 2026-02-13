import logging
from panda_server.dao.backtest_dao import BacktestTradeDAO
from common.backtest.model.backtest_trade import BacktestTradeModel
from panda_server.models.backtest.query_trade_response import (
    QueryBacktestTradeListResponse,
    QueryBacktestTradeListResponseData,
)

logger = logging.getLogger(__name__)


def _safe_float(value, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (ValueError, TypeError):
        return default


def _safe_int(value, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(float(value))
    except (ValueError, TypeError):
        return default


def _normalize_direction(direction, business=None) -> int:
    """
    Normalize to frontend-consistent integer direction:
    - positive: buy
    - non-positive: sell

    Source compatibility:
    - engine raw: 0=buy, 1=sell
    - mapped/legacy: 1=buy, -1=sell
    - string: buy/sell/买入/卖出
    """
    if direction is None and business is not None:
        direction = business

    if isinstance(direction, str):
        direction_lower = direction.strip().lower()
        if direction_lower in ["buy", "买入", "long", "b"]:
            return 1
        if direction_lower in ["sell", "卖出", "short", "s"]:
            return -1

        if direction_lower == "0":
            return 1
        if direction_lower == "1":
            return -1
        if direction_lower == "-1":
            return -1
        try:
            numeric_direction = int(float(direction_lower))
        except (ValueError, TypeError):
            return -1
        if numeric_direction == 0:
            return 1
        if numeric_direction == 1:
            return -1
        return 1 if numeric_direction > 0 else -1

    if isinstance(direction, (int, float)):
        numeric_direction = int(direction)
        if numeric_direction == 0:
            return 1
        if numeric_direction == 1:
            return -1
        return 1 if numeric_direction > 0 else -1

    return -1


async def backtest_trade_get_logic(
    back_id: str,
    page: int = 1,
    page_size: int = 10,
) -> QueryBacktestTradeListResponse:
    """Get paginated backtest trades and normalize fields for API model."""
    data_list, total_count = await BacktestTradeDAO.list_by_back_id(back_id, page, page_size)

    validated_items = []
    for data in data_list:
        try:
            mapped_data = {}

            if "_id" in data:
                mapped_data["_id"] = data["_id"]
            if "back_id" in data:
                mapped_data["back_id"] = data["back_id"]

            symbol = data.get("symbol") or data.get("contract_code") or data.get("code")
            if symbol:
                symbol_str = str(symbol).strip()
                if symbol_str:
                    mapped_data["contract_code"] = symbol_str

            contract_name = data.get("contract_name") or data.get("name")
            if contract_name:
                contract_name_str = str(contract_name).strip()
                if contract_name_str:
                    mapped_data["contract_name"] = contract_name_str

            trade_date = (
                data.get("date")
                or data.get("trade_date")
                or data.get("gmt_create")
                or data.get("created_at")
            )
            if trade_date is not None:
                trade_date_str = str(trade_date).strip()
                if trade_date_str:
                    mapped_data["trade_date"] = trade_date_str

            trade_time = data.get("time") or data.get("gmt_create_time")
            if trade_time is not None:
                trade_time_str = str(trade_time).strip()
                if trade_time_str:
                    mapped_data["gmt_create_time"] = trade_time_str
                    mapped_data["gmt_create"] = trade_time_str

            mapped_data["direction"] = _normalize_direction(
                data.get("direction"),
                data.get("business"),
            )

            if data.get("price") is not None:
                mapped_data["price"] = _safe_float(data.get("price"), 0.0)

            if data.get("volume") is not None:
                mapped_data["volume"] = _safe_int(data.get("volume"), 0)

            amount_value = data.get("amount")
            commission_value = data.get("commission")
            if amount_value is not None or commission_value is not None:
                mapped_data["cost"] = _safe_float(amount_value, 0.0) + _safe_float(commission_value, 0.0)
            elif mapped_data.get("price") is not None and mapped_data.get("volume") is not None:
                mapped_data["cost"] = _safe_float(mapped_data.get("price"), 0.0) * _safe_float(
                    mapped_data.get("volume"), 0.0
                )
            else:
                mapped_data["cost"] = 0.0

            validated_items.append(BacktestTradeModel.model_validate(mapped_data))
        except Exception as e:
            logger.warning(f"Trade data validation failed: {e}, raw: {data}")
            logger.debug(f"Trade mapping error details: {e}", exc_info=True)

    pagination = {
        "total": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": (total_count + page_size - 1) // page_size,
    }

    response_data = QueryBacktestTradeListResponseData(items=validated_items, pagination=pagination)
    return QueryBacktestTradeListResponse(data=response_data)
