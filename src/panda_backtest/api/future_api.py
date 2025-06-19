# -*- coding: utf-8 -*-
"""
File: stock_api.py
Author: peiqi
Date: 2025/5/29
Description:
"""
import pandas as pd
from common.connector.mongodb_handler import DatabaseHandler
from common.config.config import config

api_list = []


def append_to_api_list(func):
    """
    装饰器：将 API 函数名添加到全局的 api_list 中
    """
    api_list.append(func.__name__)
    globals()[func.__name__] = func
    return func


# 初始化数据库连接，避免每次调用时都创建新的数据库连接
quotation_mongo_db = DatabaseHandler(config=config)

"""
查询品种某一天的主力合约
"""


@append_to_api_list
def future_api_domain_symbol(symbol: str, date: str):
    # 构造 Mongo 查询条件
    query = {
        "symbol": symbol,
        "date": date
    }
    bar_dict = quotation_mongo_db.mongo_find_one(
        db_name=config["MONGO_DB"],
        collection_name='future_market',
        query=query,
        project={'_id': 0, 'symbol': 1, 'exchange': 1, 'trading_code': 1}
    )
    return bar_dict


"""
获取期货行情
"""
@append_to_api_list
def future_api_quotation(symbol_list=None, start_date=None, end_date=None, fields=None, period=None):
    # 根据 period 确定集合名称
    collection_map = {
        "1m": "future_1m_market",
        "5m": "future_5m_market",
        "15m": "future_15m_market",
        "30m": "future_30m_market",
        "1h": "future_60m_market",
        "1d": "future_market"
    }
    collection_name = collection_map.get(period)
    if not collection_name:
        raise ValueError("Invalid period value")

    # 设置要返回的字段
    fields_dict = {'_id': 0}
    if fields:
        fields_dict.update({'trade_date': 1})  # 确保返回交易日期字段
        for f in fields:
            fields_dict[f] = 1

    # 构造 Mongo 查询条件
    query = {
        "symbol": {"$in": symbol_list},
        "date": {"$gte": start_date, "$lte": end_date}
    }

    # 查询
    bar_dict = quotation_mongo_db.mongo_find(
        db_name=config["MONGO_DB"],
        collection_name=collection_name,
        query=query,
        projection=fields_dict
    )

    # 处理查询结果为空的情况
    if not bar_dict:
        return pd.DataFrame()

    # 转换查询结果为 DataFrame
    df_bar = pd.DataFrame(bar_dict)
    return df_bar


if __name__ == '__main__':
    # 测试查询主力合约
    result = future_api_domain_symbol(symbol="AG88", date="20250605")
    print(result)

    # 测试查询期货行情
    # result = future_api_quotation(symbol_list=["AG2509","AG2508"],start_date="20250420",end_date="20250430",period="1d")
    # print(result)
