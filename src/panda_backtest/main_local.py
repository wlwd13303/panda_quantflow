"""
          ┌─┐       ┌─┐
       ┌──┘ ┴───────┘ ┴──┐
       │                 │
       │       ───       │
       │  ─┬┘       └┬─  │
       │                 │
       │       ─┴─       │
       │                 │
       └───┐         ┌───┘
           │         │
           │         │
           │         │
           │         └──────────────┐
           │                        │
           │                        ├─┐
           │                        ┌─┘
           │                        │
           └─┐  ┐  ┌───────┬──┐  ┌──┘
             │ ─┤ ─┤       │ ─┤ ─┤
             └──┴──┘       └──┴──┘
                 神兽保佑
                 代码无BUG!
"""
from panda_backtest.config.dev_init import DevInit
from importlib import import_module
from panda_backtest.backtest_common.system.context.core_context import CoreContext
from panda_backtest.backtest_common.system.event.engine import Engine
from panda_backtest.backtest_common.system.compile.strategy import Strategy
from panda_backtest.backtest_common.system.compile.strategy_utils import FileStrategyLoader
import traceback
from panda_backtest.data.context.strategy_context import StrategyContext
from panda_backtest.system.panda_log import SRLogger
import json
import pandas as pd
from pathlib import Path
import asyncio
from panda_server.config.sqlite_database import sqlite_db
from panda_server.config.env import SQLITE_DB_PATH


class Run(object):

    @staticmethod
    def start(handle_message):
        # # LogFactory.init_logger() - 已替换为统一日志配置

        # 初始化 SQLite 数据库路径（必须在其他操作之前）
        # 获取项目根目录并解析数据库路径
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        db_path = project_root / SQLITE_DB_PATH
        sqlite_db.set_db_path(str(db_path))
        
        # 初始化数据库表结构（如果需要）
        try:
            # 尝试创建新的事件循环来运行异步初始化
            asyncio.run(sqlite_db.init_database())
        except RuntimeError:
            # 如果事件循环已经在运行，使用当前循环
            loop = asyncio.get_event_loop()
            if not loop.is_running():
                loop.run_until_complete(sqlite_db.init_database())
            else:
                # 如果循环正在运行，创建一个新线程来运行
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, sqlite_db.init_database())
                    future.result()
        
        # 系统核心上下文 创建q
        strategy_context = StrategyContext()
        
        # 处理优化参数
        run_params = handle_message.get('run_params', None)
        if run_params is not None and run_params != 'no_opz' and run_params != 'no_run_params' and run_params != '':
            print('运行时参数', run_params)
            param_dict = dict()
            run_params_list = json.loads(run_params)
            for run_params_item in run_params_list:
                if run_params_item[0] == 0:
                    param_dict[run_params_item[1]] = float(run_params_item[2])
                elif run_params_item[0] == 1:
                    param_dict[run_params_item[1]] = run_params_item[2]
                elif run_params_item[0] == 2:
                    try:
                        json_data = json.loads(run_params_item[2])
                        df = pd.json_normalize(json_data)
                        param_dict[run_params_item[1]] = df
                    except Exception as e:
                        print(f"Error loading JSON DataFrame : {e}")
            strategy_context.init_opz_params(param_dict)
        
        _context = CoreContext(strategy_context)

        back_test_id = handle_message['back_test_id']
        DevInit.init_log_env('panda')
        DevInit.init_remote_sr_log(back_test_id, handle_message.get('run_params', 'no_run_params'), strategy_context)

        # 全局动态字典初始化
        global_args = {}

        run_type = 6

        # 风控相关
        # strategy_risk_control_list = handle_message.get('strategy_risk_control_list', None)
        # risk_control_manager = RiskControlManager(MongoClient.get_mongo_db(), _context.event_bus, strategy_context)
        # risk_control_manager.load_local_risk_control(strategy_risk_control_list)
        # risk_control_manager.init_event()
        # _context.set_risk_control_manager(risk_control_manager)

        global_args = FileStrategyLoader(handle_message['file'], True).load(global_args)
        handle_message['strategy_id'] = 1
        extension_module = import_module("panda_backtest.extensions.trade_reverse_future")
        extension = extension_module.load_extension()
        extension.create(_context)
        Strategy(global_args, _context.event_bus)

        # SRLogger.info(str(handle_message))
        # 项目启动
        try:
            Engine(_context).run(handle_message)
        except Exception as e:
            print(traceback.format_exc())
            print(str(e))

        SRLogger.end()



