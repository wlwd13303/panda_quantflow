import logging
from fastapi import HTTPException, status
from panda_server.dao.backtest_dao import BacktestProfitDAO
from common.backtest.model.backtest_profit import BacktestProfitModel
from panda_server.models.backtest.query_profit_response import QueryBacktestProfitListResponse, QueryBacktestProfitListResponseData

logger = logging.getLogger(__name__)


async def backtest_profit_get_logic(
    back_id: str,
    page: int = 1,
    page_size: int = 10
) -> QueryBacktestProfitListResponse:
    """
    根据回测ID分页获取回测收益信息，并做模型校验，返回统一结构
    """
    # 使用 SQLite DAO 获取收益数据
    data_list, total_count = await BacktestProfitDAO.list_by_back_id(back_id, page, page_size)
    
    validated_items = []
    for data in data_list:
        try:
            # 字段映射：将数据库字段映射为模型期望的字段
            mapped_data = {}
            
            # 基础字段直接复制
            if '_id' in data:
                mapped_data['_id'] = data['_id']
            if 'back_id' in data:
                mapped_data['back_id'] = data['back_id']
            
            # date -> gmt_create_time 和 gmt_create (前端期望的字段)
            if 'date' in data:
                date_value = data['date']
                if date_value:
                    date_str = str(date_value).strip()
                    if date_str:
                        mapped_data['date'] = date_str
                        mapped_data['gmt_create_time'] = date_str
                        mapped_data['gmt_create'] = date_str
                    else:
                        mapped_data['date'] = None
                        mapped_data['gmt_create_time'] = None
                        mapped_data['gmt_create'] = None
                else:
                    mapped_data['date'] = None
                    mapped_data['gmt_create_time'] = None
                    mapped_data['gmt_create'] = None
            
            # total_value 字段（账户总价值，前端需要）
            if 'total_value' in data and data['total_value'] is not None:
                mapped_data['total_value'] = float(data['total_value'])
            
            # profit -> day_profit (日收益)
            if 'profit' in data and data['profit'] is not None:
                mapped_data['profit'] = float(data['profit'])
                mapped_data['day_profit'] = float(data['profit'])
            
            # cumulative_profit -> strategy_profit 和 total_profit (累计收益 -> 策略收益)
            if 'cumulative_profit' in data and data['cumulative_profit'] is not None:
                mapped_data['cumulative_profit'] = float(data['cumulative_profit'])
                mapped_data['strategy_profit'] = float(data['cumulative_profit'])
                mapped_data['total_profit'] = float(data['cumulative_profit'])
            
            # profit_rate -> profit_rate (收益率)
            if 'profit_rate' in data and data['profit_rate'] is not None:
                mapped_data['profit_rate'] = float(data['profit_rate'])
            
            # cumulative_profit_rate (累计收益率)
            if 'cumulative_profit_rate' in data and data['cumulative_profit_rate'] is not None:
                mapped_data['cumulative_profit_rate'] = float(data['cumulative_profit_rate'])
            
            # 如果total_value存在但strategy_profit不存在，使用total_value作为total_profit
            if 'total_value' in mapped_data and mapped_data.get('total_value') is not None:
                if 'total_profit' not in mapped_data or mapped_data.get('total_profit') is None:
                    mapped_data['total_profit'] = mapped_data['total_value']
            
            validated = BacktestProfitModel.model_validate(mapped_data)
            validated_items.append(validated)
        except Exception as e:
            logger.warning(f"Profit data validation failed: {e}, raw: {data}")
            logger.debug(f"Mapping error details: {e}", exc_info=True)
    
    pagination = {
        "total": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": (total_count + page_size - 1) // page_size
    }
    response_data = QueryBacktestProfitListResponseData(items=validated_items, pagination=pagination)
    return QueryBacktestProfitListResponse(data=response_data) 