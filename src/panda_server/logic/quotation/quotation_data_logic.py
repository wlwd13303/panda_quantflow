"""
行情数据业务逻辑
复用 panda_backtest 的数据查询逻辑
"""
import logging
from typing import List, Optional
from datetime import datetime

from common.connector.mongodb_handler import DatabaseHandler
from common.config.config import config

logger = logging.getLogger(__name__)


class QuotationDataLogic:
    """行情数据查询逻辑"""
    
    def __init__(self):
        self.quotation_mongo_db = DatabaseHandler(config=config)
        self.db_name = config["MONGO_DB"]
    
    def get_live_data(
        self,
        quotation: str,
        quotation_type: str = "stock",
        period: str = "1m",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 500
    ) -> List[dict]:
        """
        获取实时行情数据
        
        Args:
            quotation: 股票代码，如 '000009.SZ'
            quotation_type: 行情类型 stock/future/index
            period: 周期 1m/5m/15m/30m/1h/1d
            start_date: 开始日期 YYYYMMDD，可选
            end_date: 结束日期 YYYYMMDD，可选
            limit: 返回数据条数限制
            
        Returns:
            K线数据列表
        """
        try:
            # 确定collection名称和查询条件
            collection_name, query = self._build_query(
                quotation, quotation_type, period, start_date, end_date
            )
            
            logger.info(f"查询行情数据: collection={collection_name}, query={query}, limit={limit}")
            
            # 查询数据
            result = self.quotation_mongo_db.mongo_find(
                db_name=self.db_name,
                collection_name=collection_name,
                query=query,
                projection={'_id': 0},
                sort=[('trade_date', -1), ('time', -1)] if period != '1d' else [('date', -1)]
            )
            
            # 反转结果，使其按时间正序排列
            if result:
                result = list(reversed(result))
            
            # 手动限制返回条数
            if result and limit and len(result) > limit:
                result = result[:limit]
            
            logger.info(f"查询到 {len(result) if result else 0} 条数据")
            return result or []
            
        except Exception as e:
            logger.error(f"查询行情数据失败: {e}", exc_info=True)
            raise
    
    def _build_query(
        self,
        quotation: str,
        quotation_type: str,
        period: str,
        start_date: Optional[str],
        end_date: Optional[str]
    ) -> tuple:
        """
        构建查询条件
        
        Returns:
            (collection_name, query_dict)
        """
        # 如果没有指定日期，使用今天
        if not end_date:
            end_date = datetime.now().strftime('%Y%m%d')
        if not start_date:
            start_date = end_date
        
        # 根据类型和周期确定collection
        if quotation_type == "stock":
            if period == "1d":
                collection_name = "stock_market"
                query = {
                    "symbol": quotation,
                    "date": {"$gte": start_date, "$lte": end_date}
                }
            else:
                # 分钟线数据
                collection_name = "stock_quotation_min_data"
                query = {
                    "symbol": quotation,
                    "trade_date": {"$gte": int(start_date), "$lte": int(end_date)}
                }
        elif quotation_type == "future":
            if period == "1d":
                collection_name = "future_1d_market"
                # 期货需要去掉后缀
                symbol_prefix = quotation.split(".")[0] if "." in quotation else quotation
                query = {
                    "symbol": symbol_prefix,
                    "date": {"$gte": start_date, "$lte": end_date}
                }
            else:
                collection_name = "future_quotation_min_data_v2"
                query = {
                    "symbol": quotation,
                    "trade_date": {"$gte": int(start_date), "$lte": int(end_date)}
                }
        elif quotation_type == "index":
            if period == "1d":
                collection_name = "index_market"
                query = {
                    "symbol": quotation,
                    "date": {"$gte": start_date, "$lte": end_date}
                }
            else:
                # 指数分钟线使用股票分钟线collection
                collection_name = "stock_quotation_min_data"
                query = {
                    "symbol": quotation,
                    "trade_date": {"$gte": int(start_date), "$lte": int(end_date)}
                }
        else:
            raise ValueError(f"不支持的行情类型: {quotation_type}")
        
        return collection_name, query


# 创建单例实例
quotation_logic = QuotationDataLogic()

