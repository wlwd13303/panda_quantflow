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
            # 字段映射：将数据库字段映射为模型期望的字段
            mapped_data = {}
            
            # 基础字段直接复制
            if '_id' in data:
                mapped_data['_id'] = data['_id']
            if 'back_id' in data:
                mapped_data['back_id'] = data['back_id']
            
            # symbol -> contract_code (前端期望的字段)
            if 'symbol' in data and data['symbol']:
                mapped_data['contract_code'] = data['symbol']
                mapped_data['code'] = data['symbol']  # 也设置code字段，兼容前端
            
            # date -> trade_date 和 gmt_create_time (前端期望的字段)
            if 'date' in data:
                date_value = data['date']
                if date_value:
                    date_str = str(date_value).strip()
                    if date_str:
                        mapped_data['trade_date'] = date_str
                        mapped_data['gmt_create_time'] = date_str
                        mapped_data['date'] = date_str  # 保持原字段
                    else:
                        # 如果date为空字符串，设置None而不是空字符串
                        mapped_data['trade_date'] = None
                        mapped_data['gmt_create_time'] = None
                else:
                    mapped_data['trade_date'] = None
                    mapped_data['gmt_create_time'] = None
            
            # time -> gmt_create (如果需要)
            if 'time' in data and data['time']:
                mapped_data['gmt_create'] = str(data['time'])
            
            # direction 字段处理：转换为数字格式
            # 注意：回测引擎中 SIDE_BUY=0(买入), SIDE_SELL=1(卖出)
            # 前端期望：direction > 0 买入，direction <= 0 卖出
            if 'direction' in data:
                direction = data['direction']
                if isinstance(direction, str):
                    # 字符串转数字：buy->1, sell->-1, 其他->0
                    direction_lower = direction.lower()
                    if direction_lower in ['buy', '买入', '0']:
                        mapped_data['direction'] = 1  # 买入
                    elif direction_lower in ['sell', '卖出', '1']:
                        mapped_data['direction'] = -1  # 卖出
                    else:
                        mapped_data['direction'] = -1  # 默认卖出
                elif isinstance(direction, (int, float)):
                    # 0 (SIDE_BUY) -> 1 (买入), 1 (SIDE_SELL) -> -1 (卖出)
                    if int(direction) == 0:
                        mapped_data['direction'] = 1  # 买入
                    else:
                        mapped_data['direction'] = -1  # 卖出
                else:
                    mapped_data['direction'] = -1  # 默认卖出
            else:
                mapped_data['direction'] = -1  # 默认卖出
            
            # price 字段
            if 'price' in data:
                mapped_data['price'] = data['price']
            
            # volume -> volume (数量)
            if 'volume' in data and data['volume'] is not None:
                mapped_data['volume'] = data['volume']
                # 前端期望amount字段是数量
                mapped_data['amount'] = data['volume']
            
            # amount -> cost (金额，前端期望cost字段)
            # 只有当 amount 不为 None 时才设置 cost
            if 'amount' in data and data['amount'] is not None:
                try:
                    mapped_data['cost'] = float(data['amount'])
                except (ValueError, TypeError):
                    mapped_data['cost'] = 0.0
            
            # commission 字段处理：将佣金加到成本中
            # 只有当 commission 不为 None 时才处理
            if 'commission' in data and data['commission'] is not None:
                try:
                    commission_value = float(data['commission'])
                except (ValueError, TypeError):
                    commission_value = 0.0
                current_cost = mapped_data.get('cost')
                if current_cost is None:
                    current_cost = 0.0
                mapped_data['cost'] = float(current_cost) + commission_value
            
            # offset 字段
            if 'offset' in data:
                mapped_data['offset'] = data['offset']
            
            # 如果amount字段不存在，尝试从volume计算
            if 'amount' not in mapped_data and 'volume' in mapped_data and mapped_data.get('volume') is not None:
                mapped_data['amount'] = mapped_data['volume']
            
            # 如果cost字段不存在或为None，尝试从price和volume计算
            if 'cost' not in mapped_data or mapped_data.get('cost') is None:
                if 'price' in mapped_data and mapped_data.get('price') is not None and 'volume' in mapped_data and mapped_data.get('volume') is not None:
                    price = float(mapped_data.get('price', 0)) or 0.0
                    volume = float(mapped_data.get('volume', 0)) or 0.0
                    mapped_data['cost'] = price * volume
                else:
                    mapped_data['cost'] = 0.0
            elif mapped_data.get('cost') is None:
                mapped_data['cost'] = 0.0
            
            validated = BacktestTradeModel.model_validate(mapped_data)
            validated_items.append(validated)
        except Exception as e:
            logger.warning(f"Trade data validation failed: {e}, raw: {data}")
            logger.debug(f"Mapping error details: {e}", exc_info=True)
    
    pagination = {
        "total": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": (total_count + page_size - 1) // page_size
    }
    response_data = QueryBacktestTradeListResponseData(items=validated_items, pagination=pagination)
    return QueryBacktestTradeListResponse(data=response_data) 