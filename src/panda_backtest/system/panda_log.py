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
from panda_backtest.util.time.time_util import TimeUtil
from panda_server.dao.backtest_dao import BacktestDAO

class SRLogger:
    _strategy_context = None
    _back_test_id = None
    _opz_params_str = None
    _log_queue = None
    _process_queue = queue.Queue()
    _sort = 0
    _insert_flag = True

    @staticmethod
    def _echo_to_console(log_type, content):
        if log_type < 0:
            return
        logger = logging.getLogger("SRLogger")
        level_map = {
            1: logging.INFO,
            2: logging.WARNING,
            3: logging.DEBUG,
            4: logging.ERROR,
        }
        logger.log(level_map.get(log_type, logging.INFO), f"[SRLogger] {content}")

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
    def warning(content):
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
        try:
            # 检查日志队列是否已初始化，如果未初始化则进行懒加载初始化
            if SRLogger._log_queue is None:
                # 自动初始化日志队列和消费线程（用于非回测场景）
                SRLogger._log_queue = queue.Queue()
                log_thread = threading.Thread(target=SRLogger.log_consume)
                log_thread.daemon = True  # 设置为守护线程，主程序退出时自动结束
                log_thread.start()
            
            insert_content = dict()
            insert_content['level'] = log_type
            insert_content['relation_id'] = SRLogger._back_test_id
            insert_content['opz_params_str'] = SRLogger._opz_params_str
            insert_content['insert_time'] = TimeUtil.datetime_to_utc(datetime.datetime.now())
            
            # 安全获取 exhibit_time，避免 trade_time 为 None 导致异常
            if SRLogger._strategy_context and hasattr(SRLogger._strategy_context, 'trade_time') and SRLogger._strategy_context.trade_time:
                try:
                    insert_content['exhibit_time'] = TimeUtil.datetime_to_utc(SRLogger._strategy_context.trade_time)
                except Exception as e:
                    # 如果转换失败，使用当前时间
                    insert_content['exhibit_time'] = TimeUtil.datetime_to_utc(datetime.datetime.now())
                    logging.warning(f"转换 trade_time 失败，使用当前时间: {e}")
            else:
                # 如果 trade_time 不可用，使用 insert_time
                insert_content['exhibit_time'] = insert_content['insert_time']
            
            insert_content['run_info'] = content
            insert_content['sort'] = SRLogger._sort
            insert_content['content_type'] = content_type
            insert_content['source'] = source
            if risk_control_name is not None:
                insert_content['risk_control_name'] = risk_control_name
            SRLogger._echo_to_console(log_type, content)
            SRLogger._sort = SRLogger._sort + 1
            SRLogger._log_queue.put_nowait(insert_content)
        except Exception as e:
            # 如果日志记录失败，打印错误但不影响主流程
            print(f"[SRLogger] 日志记录失败: {e}")
            logging.error(f"日志记录失败: {e}")
            import traceback
            traceback.print_exc()

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
        """消费日志队列，将日志写入 SQLite 数据库"""
        log_list = list()
        while True:
            try:
                insert_content = SRLogger._log_queue.get(timeout=12 * 60 * 60)
                if insert_content['level'] == -1:
                    print('日志线程收到结束信号')
                    # 收到结束信号，批量写入剩余日志
                    if len(log_list) > 0:
                        SRLogger._batch_insert_logs_to_sqlite(log_list)
                        SRLogger._insert_flag = False
                        break
                log_list.append(insert_content)
                # 当日志累积到50条时，批量写入
                if len(log_list) > 50:
                    insert_log_list = copy.deepcopy(log_list)
                    log_list = list()
                    SRLogger._batch_insert_logs_to_sqlite(insert_log_list)

            except queue.Empty:
                print('日志超时')
                # 超时时写入剩余日志
                if len(log_list) > 0:
                    SRLogger._batch_insert_logs_to_sqlite(log_list)
                break
            except Exception as e:
                logging.error(f"日志消费失败: {e}")
                break
    
    @staticmethod
    def _batch_insert_logs_to_sqlite(log_list):
        """批量将日志插入 SQLite 数据库（带重试机制）"""
        max_retries = 3
        retry_delay = 0.5  # 秒
        
        try:
            # 动态导入，避免循环依赖
            from panda_server.dao.backtest_dao import BacktestLogDAO
            from panda_server.config.sqlite_database import sqlite_db
            from panda_server.config.env import SQLITE_DB_PATH
            import sqlite3
            
            # 确保数据库路径已设置（回测进程中需要手动初始化）
            if sqlite_db.db_path is None:
                print(f"[SRLogger] 初始化 SQLite 数据库路径: {SQLITE_DB_PATH}")
                sqlite_db.set_db_path(SQLITE_DB_PATH)
            
            print(f"[SRLogger] 准备批量插入 {len(log_list)} 条日志到 SQLite")
            
            # 使用异步任务将日志批量插入 SQLite
            async def batch_insert():
                success_count = 0
                error_count = 0
                for log_item in log_list:
                    retry_count = 0
                    while retry_count < max_retries:
                        try:
                            # 字段映射：MongoDB -> SQLite
                            # run_info -> message
                            # exhibit_time 或 insert_time -> timestamp
                            # level -> log_level
                            await BacktestLogDAO.create(
                                relation_id=log_item.get('relation_id', ''),
                                back_id=log_item.get('relation_id', ''),  # 使用 relation_id 作为 back_id
                                log_level=str(log_item.get('level', '')),
                                message=log_item.get('run_info', ''),
                                timestamp=log_item.get('exhibit_time') or log_item.get('insert_time'),
                                sort=log_item.get('sort', 0)
                            )
                            success_count += 1
                            break  # 成功则跳出重试循环
                        except (sqlite3.OperationalError, Exception) as e:
                            error_msg = str(e)
                            if 'database is locked' in error_msg and retry_count < max_retries - 1:
                                # 数据库锁定，等待后重试
                                retry_count += 1
                                await asyncio.sleep(retry_delay * retry_count)  # 指数退避
                                continue
                            else:
                                # 其他错误或重试次数用尽
                                error_count += 1
                                if retry_count > 0:
                                    print(f"[SRLogger] 插入日志失败（重试{retry_count}次后）: {e}")
                                break
                
                print(f"[SRLogger] 批量插入完成: 成功 {success_count} 条, 失败 {error_count} 条")
            
            # 在同步上下文中运行异步函数
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # 如果事件循环正在运行，创建新的线程来运行
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(asyncio.run, batch_insert())
                        future.result(timeout=60)  # 60秒超时
                else:
                    # 如果事件循环未运行，直接运行
                    loop.run_until_complete(batch_insert())
            except RuntimeError as e:
                # 如果没有事件循环，创建一个新的
                asyncio.run(batch_insert())
            
        except Exception as e:
            import traceback
            print(f"[SRLogger] 批量插入日志到 SQLite 失败: {e}")
            logging.error(f"批量插入日志到 SQLite 失败: {e}\n{traceback.format_exc()}")
