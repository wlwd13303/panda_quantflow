import logging
from fastapi import HTTPException, status
from panda_server.dao.backtest_dao import BacktestPositionDAO, BacktestAccountDAO
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

    # 获取账户总价值信息
    account_list, _ = await BacktestAccountDAO.list_by_back_id(back_id, page=1, page_size=100000)
    account_total_value_map = {}
    for account in account_list:
        date_key = account.get('date')
        if not date_key:
            continue
        total_value = account.get('total_value')
        if total_value is None:
            continue
        account_total_value_map[date_key] = float(total_value)

    validated_items = []
    for data in data_list:
        try:
            # 计算每日持仓比例（方案C）：市值 / （总资产 + 总负债）
            date_key = data.get('date')
            market_value = data.get('market_value') or 0
            total_asset = account_total_value_map.get(date_key) or 0
            position_ratio = None
            if market_value and total_asset:
                try:
                    position_ratio = float(market_value) / float(total_asset)
                except Exception:
                    position_ratio = None

            # 字段映射：数据库字段 → 模型字段
            mapped_data = {
                **data,
                'contract_code': data.get('symbol'),
                'contract_name': data.get('contract_name'),
                'position': int(data.get('volume') or 0),
                'price': data.get('avg_price'),
                'last_price': data.get('market_price'),
                'gmt_create': data.get('created_at') or data.get('date'),
                'position_ratio': position_ratio,
            }
            validated = BacktestPositionModel.model_validate(mapped_data)
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