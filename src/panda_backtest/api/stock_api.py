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
    api_list.append(func.__name__)
    globals()[func.__name__] = func
    return func

"""
获取股票的pre_close
"""
@append_to_api_list
def stock_api_pre_close(df_stock_code: pd.DataFrame, date: str):
    # 初始化数据库连接
    quotation_mongo_db = DatabaseHandler(config=config)
    stock_code_list=df_stock_code['symbol'].tolist()
    # 构造 Mongo 查询条件
    query = {
        "symbol": {"$in": stock_code_list},  # 注意这里
        "date": date
    }

    # 查询
    bar_dict = quotation_mongo_db.mongo_find(
        db_name=config["MONGO_DB"],
        # collection_name='stock_daily_quotation',
        collection_name='stock_market',
        query=query,
        projection={'_id': 0, 'symbol': 1, 'pre_close': 1}
    )
    df_bar = pd.DataFrame(bar_dict)
    return df_bar