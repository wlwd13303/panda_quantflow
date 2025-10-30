# -*- coding: utf-8 -*-
"""
File: panda_log.py
Author: peiqi
Date: 2025/5/14
Description: 
"""
import copy
import logging

import datetime
import time
import pandas
import queue
import threading
import asyncio
from common.connector.mongodb_handler import DatabaseHandler
from panda_backtest.util.time.time_util import TimeUtil
from common.config.config import config
from panda_server.dao.backtest_dao import BacktestDAO

class SRLogger:
    _strategy_context = None
    _back_test_id = None
    _opz_params_str = None
    _log_queue = None
    _process_queue = queue.Queue()
    _sort = 0
    _insert_flag = True

    @classmethod
    def init_strategy_context(cls, back_test_id, opz_params_str, strategy_context):
        SRLogger._log_queue = queue.Queue()
        SRLogger._strategy_context = strategy_context
        SRLogger._back_test_id = back_test_id
        SRLogger._opz_params_str = opz_params_str
        log_thread = threading.Thread(target=cls.log_consume)
        log_thread.start()
        process_thread = threading.Thread(target=cls.process_consume)
        process_thread.setDaemon(True)
        process_thread.start()

    @staticmethod
    def info(content):
        if isinstance(content, pandas.DataFrame):
            content = content.to_html()
            SRLogger.log_provide(content, 1, 1)
        else:
            content = str(content)
            SRLogger.log_provide(content, 1)

    @staticmethod
    def error(content):
        if isinstance(content, pandas.DataFrame):
            content = content.to_html()
            SRLogger.log_provide(content, 4, 1)
        else:
            content = str(content)
            SRLogger.log_provide(content, 4)

    @staticmethod
    def warn(content):
        if isinstance(content, pandas.DataFrame):
            content = content.to_html()
            SRLogger.log_provide(content, 2, 1)
        else:
            content = str(content)
            SRLogger.log_provide(content, 2)

    @staticmethod
    def debug(content):
        if isinstance(content, pandas.DataFrame):
            content = content.to_html()
            SRLogger.log_provide(content, 3, 1)
        else:
            content = str(content)
            SRLogger.log_provide(content, 3)

    @staticmethod
    def risk(risk_control_name, content):
        if isinstance(content, pandas.DataFrame):
            content = content.to_html()
            SRLogger.log_provide(content, 1, 1, 1, risk_control_name)
        else:
            content = str(content)
            SRLogger.log_provide(content, 1, 0, 1, risk_control_name)

    @staticmethod
    def end():
        t_end = time.time() + 20
        SRLogger.log_provide('日志进程结束啦', -1)
        while SRLogger._insert_flag and time.time() < t_end:
            continue

    @staticmethod
    def performance_analysis(content):
        print('performance_analysis==>' + str(content))

    @staticmethod
    def process(current, total):
        progress_rate = int(current / total * 100)
        if progress_rate % 1 == 0:
            insert_content = dict()
            insert_content['level'] = 0
            insert_content['progress_rate'] = progress_rate
            SRLogger._process_queue.put_nowait(insert_content)

    @staticmethod
    def log_provide(content, log_type, content_type=0, source=0, risk_control_name=None):
        insert_content = dict()
        insert_content['level'] = log_type
        insert_content['relation_id'] = SRLogger._back_test_id
        insert_content['opz_params_str'] = SRLogger._opz_params_str
        insert_content['insert_time'] = TimeUtil.datetime_to_utc(datetime.datetime.now())
        insert_content['exhibit_time'] = TimeUtil.datetime_to_utc(SRLogger._strategy_context.trade_time)
        # 如果 strategy_context 为 None，则 exhibit_time 设置为空
        # if SRLogger._strategy_context and hasattr(SRLogger._strategy_context, 'trade_time'):
        #     insert_content['exhibit_time'] = TimeUtil.datetime_to_utc(SRLogger._strategy_context.trade_time)
        # else:
        #     insert_content['exhibit_time'] = None  # 设置为空
        insert_content['run_info'] = content
        insert_content['sort'] = SRLogger._sort
        insert_content['content_type'] = content_type
        insert_content['source'] = source
        if risk_control_name is not None:
            insert_content['risk_control_name'] = risk_control_name
        SRLogger._sort = SRLogger._sort + 1
        SRLogger._log_queue.put_nowait(insert_content)

    @staticmethod
    def process_consume():
        """消费进度队列，更新数据库中的回测进度"""
        last_progress = -1  # 记录上次更新的进度，避免频繁更新
        
        while True:
            try:
                insert_content = SRLogger._process_queue.get(timeout=12 * 60 * 60)
                progress_rate = insert_content.get('progress_rate', 0)
                
                # 只有当进度变化时才更新数据库（避免频繁更新）
                if progress_rate != last_progress and SRLogger._back_test_id:
                    last_progress = progress_rate
                    # 异步更新进度到 SQLite
                    SRLogger._update_progress_async(SRLogger._back_test_id, float(progress_rate))
                    
            except queue.Empty:
                print('进程信息超时')
                break
            except Exception as e:
                logging.error(f"更新回测进度失败: {e}")
    
    @staticmethod
    def _update_progress_async(run_id: str, progress: float):
        """异步更新回测进度到 SQLite 数据库"""
        async def update_progress():
            try:
                await BacktestDAO.update(run_id, progress=progress)
            except Exception as e:
                logging.error(f"更新回测进度失败: {e}")
        
        try:
            # 在同步上下文中运行异步函数
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 如果事件循环正在运行，创建新的线程来运行
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, update_progress())
                    future.result(timeout=5)  # 5秒超时
            else:
                # 如果事件循环未运行，直接运行
                loop.run_until_complete(update_progress())
        except RuntimeError:
            # 如果没有事件循环，创建一个新的
            asyncio.run(update_progress())
        except Exception as e:
            logging.error(f"异步更新进度失败: {e}")

    @staticmethod
    def log_consume():
        mongo_client = DatabaseHandler(config=config)
        log_list = list()
        while True:
            try:
                insert_content = SRLogger._log_queue.get(timeout=12 * 60 * 60)
                if insert_content['level'] == -1:
                    print('日志线程收到结束信号')
                    # 收到结束信号
                    if len(log_list) > 0:
                        mongo_client.mongo_insert_many(config["MONGO_DB"], collection_name="panda_user_strategy_log", documents=log_list)
                        SRLogger._insert_flag = False
                        break
                log_list.append(insert_content)
                if len(log_list) > 50:
                    insert_log_list = copy.deepcopy(log_list)
                    log_list = list()
                    mongo_client.mongo_insert_many(config["MONGO_DB"], collection_name="panda_user_strategy_log", documents=insert_log_list)

            except queue.Empty:
                print('日志超时')
                break
