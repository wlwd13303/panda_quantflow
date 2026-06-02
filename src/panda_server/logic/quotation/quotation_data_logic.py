"""
行情数据业务逻辑
复用 panda_backtest 的数据查询逻辑
"""
import logging
from typing import List, Optional
from datetime import datetime

from common.connector.mongodb_handler import DatabaseHandler
from common.config.config import config
from panda_server.logic.quotation.quotation_cache import quotation_cache

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
        limit: int = 500,
        use_cache: bool = True
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
            use_cache: 是否使用缓存，默认True
            
        Returns:
            K线数据列表
        """
        try:
            # 尝试从缓存获取数据
            if use_cache:
                cached_data = quotation_cache.get(
                    quotation, quotation_type, period, start_date, end_date
                )
                if cached_data is not None:
                    # 应用limit限制
                    if limit and len(cached_data) > limit:
                        return cached_data[:limit]
                    return cached_data
            # 确定collection名称和查询条件
            collection_name, query = self._build_query(
                quotation, quotation_type, period, start_date, end_date
            )
            
            logger.info(f"查询行情数据: db_name={self.db_name}, collection={collection_name}, query={query}, limit={limit}")
            
            # 查询数据
            sort_field = [('trade_date', -1), ('time', -1)] if period != '1d' else [('date', -1)]
            logger.debug(f"排序字段: {sort_field}")
            
            result = self.quotation_mongo_db.mongo_find(
                db_name=self.db_name,
                collection_name=collection_name,
                query=query,
                projection={'_id': 0},
                sort=sort_field
            )
            
            logger.info(f"原始查询结果数量: {len(result) if result else 0}")
            if result and len(result) > 0:
                logger.debug(f"第一条数据样本: {result[0]}")
                logger.debug(f"第一条数据的字段: {list(result[0].keys())}")
                logger.debug(f"第一条数据是否有date字段: {'date' in result[0]}")
                logger.debug(f"第一条数据是否有trade_date字段: {'trade_date' in result[0]}")
            
            # 反转结果，使其按时间正序排列
            if result:
                result = list(reversed(result))
                logger.debug(f"反转后结果数量: {len(result)}")
            
            # 手动限制返回条数
            if result and limit and len(result) > limit:
                result = result[:limit]
                logger.debug(f"限制后结果数量: {len(result)}")
            
            logger.info(f"查询到 {len(result) if result else 0} 条数据")

            # 日线数据：合并后复权因子
            if result and period == '1d' and quotation_type == 'stock':
                result = self._merge_adj_factor(quotation, result)

            # 存入缓存（在应用limit之前）
            if use_cache and result:
                quotation_cache.set(
                    quotation, quotation_type, period, start_date, end_date, result
                )

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

    def _merge_adj_factor(self, symbol: str, data: List[dict]) -> List[dict]:
        """将后复权因子合并到日线数据中"""
        try:
            if not data:
                return data

            dates = [item.get('date', '') for item in data if item.get('date')]
            if not dates:
                return data
            min_date = min(dates)
            max_date = max(dates)

            adj_records = self.quotation_mongo_db.mongo_find(
                db_name=self.db_name,
                collection_name="adj_factor",
                query={
                    "symbol": symbol,
                    "date": {"$gte": min_date, "$lte": max_date}
                },
                projection={"_id": 0, "date": 1, "adj_factor": 1}
            )

            if not adj_records:
                return data

            adj_map = {rec['date']: rec.get('adj_factor', 1.0) for rec in adj_records}

            for item in data:
                item_date = item.get('date', '')
                item['adj_factor'] = adj_map.get(item_date, 1.0)

        except Exception as e:
            logger.warning(f"合并复权因子失败: {e}")

        return data


# 创建单例实例
quotation_logic = QuotationDataLogic()

