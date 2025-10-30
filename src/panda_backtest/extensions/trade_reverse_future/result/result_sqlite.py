"""
回测结果保存到 SQLite 数据库
用于替代原有的 MongoDB 存储
"""
import copy
import logging
import json
import queue
import threading
import time
import asyncio
from typing import List, Dict, Any

from panda_backtest.backtest_common.system.context.core_context import CoreContext
from panda_server.dao.backtest_dao import (
    BacktestDAO, 
    BacktestAccountDAO,
    BacktestPositionDAO,
    BacktestTradeDAO,
    BacktestProfitDAO
)
import jsonpickle

logger = logging.getLogger(__name__)


class ResultSQLite(object):
    """SQLite 版本的回测结果保存类"""
    
    def __init__(self):
        self.result_queue = queue.Queue()
        self.context = CoreContext.get_instance()
        self.save_flag = True
        self._backtest_initialized = False  # 标记回测主记录是否已创建
        self.result_thread = threading.Thread(target=self.save_to_db)
        self.result_thread.setDaemon(True)
        self.result_thread.start()
    
    async def _ensure_backtest_record(self):
        """确保回测主记录存在，如果不存在则创建"""
        if self._backtest_initialized:
            return
        
        try:
            strategy_context = self.context.strategy_context
            run_info = strategy_context.run_info
            run_id = run_info.run_id
            
            # 检查记录是否已存在
            existing = await BacktestDAO.get_by_run_id(run_id)
            if existing:
                self._backtest_initialized = True
                return
            
            # 创建回测主记录
            # 从 run_info 中获取参数（这些参数在 init_run_info 时已从 handle_message 设置）
            await BacktestDAO.create(
                run_id=run_id,
                strategy_name=getattr(run_info, 'strategy_name', '未知策略'),
                strategy_code=getattr(run_info, 'strategy_code', ''),
                start_date=getattr(run_info, 'start_date', ''),
                end_date=getattr(run_info, 'end_date', ''),
                start_capital=getattr(run_info, 'stock_starting_cash', 0) or getattr(run_info, 'future_starting_cash', 0),
                commission_rate=getattr(run_info, 'commission_multiplier', 0),  # 使用 commission_multiplier
                frequency=getattr(run_info, 'frequency', '1d'),
                standard_symbol=getattr(run_info, 'benchmark', ''),
                matching_type=getattr(run_info, 'matching_type', 0),
                account_id=getattr(run_info, 'stock_account', '') or getattr(run_info, 'future_account', ''),
                account_type=getattr(run_info, 'account_type', 0),
                slippage=getattr(run_info, 'slippage', 0),
                margin_rate=getattr(run_info, 'margin_multiplier', 1),  # 使用 margin_multiplier
                start_future_capital=getattr(run_info, 'future_starting_cash', 0),
                start_fund_capital=getattr(run_info, 'fund_starting_cash', 0),
                status='running',
                progress=0.0
            )
            self._backtest_initialized = True
            logger.info(f"回测主记录已创建: {run_id}")
        except Exception as e:
            logger.error(f"创建回测主记录失败: {e}")
            # 不抛出异常，让后续操作继续尝试

    def save_daily_data_to_db(self, all_account_list, all_position_list, all_trade_list, all_profit_dict):
        """保存每日数据到队列"""
        all_position_list = json.loads(jsonpickle.encode(all_position_list, unpicklable=False))
        all_trade_list = json.loads(jsonpickle.encode(all_trade_list, unpicklable=False))
        save_all_account_list = copy.deepcopy(all_account_list)
        self.result_queue.put_nowait((0, save_all_account_list, all_position_list, all_trade_list, all_profit_dict))

    def save_result_to_db(self, last_strategy_profit, ar, last_standard_profit, sr, alpha, beta, sharpe, vol,
                          md, info_ration, sortino, annual_te, kama_ratio, dw, benchmark_name):
        """保存最终回测结果"""
        self.save_flag = False

        # 收集队列中所有数据
        all_account_list = list()
        all_position_list = list()
        all_trade_list = list()
        all_profit_list = list()
        
        while not self.result_queue.empty():
            result_item = self.result_queue.get()
            all_account_list.extend(result_item[1])
            all_position_list.extend(result_item[2])
            all_trade_list.extend(result_item[3])
            all_profit_list.append(result_item[4])

        # 保存各类数据
        if len(all_account_list) > 0:
            self._run_async(self.save_account(all_account_list))
        if len(all_trade_list) > 0:
            self._run_async(self.save_trade(all_trade_list))
        if len(all_position_list) > 0:
            self._run_async(self.save_position(all_position_list))
        if len(all_profit_list) > 0:
            self._run_async(self.save_profit(all_profit_list))

        # 更新回测主记录
        strategy_context = self.context.strategy_context
        run_id = strategy_context.run_info.run_id
        
        update_dict = {
            'status': 'completed',
            'progress': 100.0,
            'result': json.dumps({
                'back_profit': last_strategy_profit,
                'back_profit_year': ar,
                'benchmark_profit': last_standard_profit,
                'benchmark_profit_year': sr,
                'alpha': alpha,
                'beta': beta,
                'sharpe': sharpe,
                'volatility': vol,
                'max_drawdown': md,
                'information_ratio': info_ration,
                'sortino': sortino,
                'tracking_error': annual_te,
                'kama_ratio': kama_ratio,
                'downside_risk': dw,
                'benchmark_name': benchmark_name,
                'time_consume': time.time() - strategy_context.run_info.start_run_time,
                'custom_tag': strategy_context.run_info.custom_tag,
            }),
            'completed_at': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        self._run_async(BacktestDAO.update(run_id, **update_dict))
        logger.info(f"回测 {run_id} 结果保存完成")

    def save_to_db(self):
        """后台线程持续保存数据"""
        while self.save_flag:
            try:
                result_item = self.result_queue.get(timeout=1)
                if result_item[0] == 0:
                    result_item_account_list = result_item[1]
                    all_position_list = result_item[2]
                    all_trade_list = result_item[3]
                    all_profit_dict = result_item[4]
                    
                    if len(result_item_account_list) > 0:
                        self._run_async(self.save_account(result_item_account_list))
                    if len(all_position_list) > 0:
                        self._run_async(self.save_position(all_position_list))
                    if len(all_trade_list) > 0:
                        self._run_async(self.save_trade(all_trade_list))
                    if len(all_profit_dict) > 0:
                        self._run_async(self.save_profit(all_profit_dict))
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"保存数据出错: {e}")

    async def save_account(self, account_list: List[Dict]):
        """保存账户数据"""
        try:
            # 确保回测主记录存在
            await self._ensure_backtest_record()
            
            strategy_context = self.context.strategy_context
            back_id = strategy_context.run_info.run_id
            
            for account in account_list:
                # 字段映射：将原始字段名映射到数据库字段名
                # 原始字段: gmt_create, available_funds, total_profit, static_profit, market_value, daily_pnl, holding_pnl
                # 数据库字段: date, available, balance, cash, market_value, total_value, position_profit
                
                # 日期：优先使用 date，其次 gmt_create
                date = account.get('date') or account.get('gmt_create', '')
                
                # 可用资金：优先使用 available，其次 available_funds
                available = account.get('available') or account.get('available_funds')
                
                # 余额：优先使用 balance，其次 static_profit（静态权益）
                balance = account.get('balance') or account.get('static_profit')
                
                # 现金：优先使用 cash，其次 available_funds
                cash = account.get('cash') or account.get('available_funds')
                
                # 市值：使用 market_value
                market_value = account.get('market_value')
                
                # 总资产：优先使用 total_value，其次 total_profit（总权益）
                total_value = account.get('total_value') or account.get('total_profit')
                
                # 持仓盈亏：优先使用 position_profit，其次 holding_pnl，再次 daily_pnl
                position_profit = account.get('position_profit') or account.get('holding_pnl') or account.get('daily_pnl')
                
                await BacktestAccountDAO.create(
                    back_id=back_id,
                    date=date,
                    available=available,
                    balance=balance,
                    cash=cash,
                    market_value=market_value,
                    total_value=total_value,
                    position_profit=position_profit
                )
            logger.debug(f"保存 {len(account_list)} 条账户数据")
        except Exception as e:
            logger.error(f"保存账户数据失败: {e}")

    async def save_position(self, all_position_list: List[Dict]):
        """保存持仓数据"""
        try:
            # 确保回测主记录存在
            await self._ensure_backtest_record()
            
            strategy_context = self.context.strategy_context
            back_id = strategy_context.run_info.run_id
            
            for position in all_position_list:
                # 字段映射：将原始字段名映射到数据库字段名
                # 原始字段: contract_code, position, last_price, market_value, accumulate_profit, sellable, holding_pnl, price
                # 数据库字段: date, symbol, volume, available, avg_price, market_price, market_value, profit, profit_rate
                
                # 日期：优先使用 date，其次 gmt_create
                date = position.get('date') or position.get('gmt_create', '')
                
                # 股票代码：优先使用 symbol，其次 contract_code
                symbol = position.get('symbol') or position.get('contract_code', '')
                
                # 持仓数量：优先使用 volume，其次 position
                volume = position.get('volume') or position.get('position')
                
                # 可用数量：优先使用 available，其次 sellable
                available = position.get('available') or position.get('sellable')
                
                # 持仓均价：优先使用 avg_price，其次 price
                avg_price = position.get('avg_price') or position.get('price')
                
                # 最新价：优先使用 market_price，其次 last_price
                market_price = position.get('market_price') or position.get('last_price')
                
                # 市值：使用 market_value
                market_value = position.get('market_value')
                
                # 盈亏：优先使用 profit，其次 holding_pnl，再次 accumulate_profit
                profit = position.get('profit') or position.get('holding_pnl') or position.get('accumulate_profit')
                
                # 盈亏率：优先使用 profit_rate，如果没有且有 profit 和 market_value，则计算
                profit_rate = position.get('profit_rate')
                if profit_rate is None and profit is not None and market_value is not None and market_value != 0:
                    profit_rate = profit / (market_value - profit) if (market_value - profit) != 0 else None
                
                await BacktestPositionDAO.create(
                    back_id=back_id,
                    date=date,
                    symbol=symbol,
                    volume=volume,
                    available=available,
                    avg_price=avg_price,
                    market_price=market_price,
                    market_value=market_value,
                    profit=profit,
                    profit_rate=profit_rate
                )
            logger.debug(f"保存 {len(all_position_list)} 条持仓数据")
        except Exception as e:
            logger.error(f"保存持仓数据失败: {e}")

    async def save_trade(self, all_trade_list: List[Dict]):
        """保存交易数据"""
        try:
            # 确保回测主记录存在
            await self._ensure_backtest_record()
            
            logger.debug(f"save_trade 开始处理数据，类型: {type(all_trade_list)}")
            strategy_context = self.context.strategy_context
            back_id = strategy_context.run_info.run_id
            
            for trade in all_trade_list:
                # 字段映射：将原始字段名映射到数据库字段名
                # 原始字段: gmt_create, gmt_create_time, contract_code, business, volume, price, cost, direction, trade_date
                # 数据库字段: date, time, symbol, direction, offset, price, volume, amount, commission
                
                # 日期：优先使用 date，其次 trade_date，再次 gmt_create
                date = trade.get('date') or trade.get('trade_date') or trade.get('gmt_create', '')
                
                # 时间：优先使用 time，其次 gmt_create_time
                time = trade.get('time') or trade.get('gmt_create_time', '')
                
                # 股票代码：优先使用 symbol，其次 contract_code
                symbol = trade.get('symbol') or trade.get('contract_code', '')
                
                # 方向：优先使用 direction，其次根据 business 判断（0：买  1：卖）
                direction = trade.get('direction')
                if direction is None:
                    business = trade.get('business')
                    if business == 0:
                        direction = 'buy'
                    elif business == 1:
                        direction = 'sell'
                    else:
                        direction = ''
                
                # 开平：优先使用 offset
                offset = trade.get('offset', '')
                
                # 价格：使用 price
                price = trade.get('price')
                
                # 数量：使用 volume
                volume = trade.get('volume')
                
                # 成交金额：优先使用 amount，如果没有则计算 price * volume
                amount = trade.get('amount')
                if amount is None and price is not None and volume is not None:
                    amount = price * volume
                
                # 手续费：优先使用 commission，其次 cost
                commission = trade.get('commission') or trade.get('cost')
                
                await BacktestTradeDAO.create(
                    back_id=back_id,
                    date=date,
                    time=time,
                    symbol=symbol,
                    direction=direction,
                    offset=offset,
                    price=price,
                    volume=volume,
                    amount=amount,
                    commission=commission
                )
            logger.debug(f"保存 {len(all_trade_list)} 条交易数据")
        except Exception as e:
            logger.error(f"保存交易数据失败: {e}")

    async def save_profit(self, all_profit_data):
        """保存收益数据"""
        try:
            # 确保回测主记录存在
            await self._ensure_backtest_record()
            
            logger.debug(f"save_profit 开始处理数据，类型: {type(all_profit_data)}")
            strategy_context = self.context.strategy_context
            back_id = strategy_context.run_info.run_id
            
            # 处理不同的数据类型
            documents = []
            if isinstance(all_profit_data, list):
                for item in all_profit_data:
                    if isinstance(item, dict):
                        documents.append(item)
                    elif hasattr(item, '__dict__'):
                        documents.append(item.__dict__)
            else:
                if isinstance(all_profit_data, dict):
                    documents = [all_profit_data]
                elif hasattr(all_profit_data, '__dict__'):
                    documents = [all_profit_data.__dict__]
            
            # 保存收益数据
            for profit in documents:
                if isinstance(profit, dict):
                    # 字段映射：将原始字段名映射到数据库字段名
                    # 原始字段: gmt_create, day_purchase, day_put, strategy_profit, day_profit, overful_profit
                    # 数据库字段: date, total_value, profit, profit_rate, cumulative_profit, cumulative_profit_rate
                    
                    # 日期：优先使用 date，其次 gmt_create
                    date = profit.get('date') or profit.get('gmt_create', '')
                    
                    # 总资产：优先使用 total_value，其次计算 day_purchase + day_put
                    total_value = profit.get('total_value')
                    if total_value is None:
                        day_purchase = profit.get('day_purchase', 0) or 0
                        day_put = profit.get('day_put', 0) or 0
                        total_value = day_purchase + day_put if (day_purchase or day_put) else None
                    
                    # 当日收益：优先使用 profit，其次 day_profit
                    day_profit = profit.get('profit') or profit.get('day_profit')
                    
                    # 当日收益率：优先使用 profit_rate，其次 strategy_profit
                    profit_rate = profit.get('profit_rate') or profit.get('strategy_profit')
                    
                    # 累计收益：优先使用 cumulative_profit
                    cumulative_profit = profit.get('cumulative_profit')
                    
                    # 累计收益率：优先使用 cumulative_profit_rate，其次 overful_profit
                    cumulative_profit_rate = profit.get('cumulative_profit_rate') or profit.get('overful_profit')
                    
                    await BacktestProfitDAO.create(
                        back_id=back_id,
                        date=date,
                        total_value=total_value,
                        profit=day_profit,
                        profit_rate=profit_rate,
                        cumulative_profit=cumulative_profit,
                        cumulative_profit_rate=cumulative_profit_rate
                    )
            
            logger.debug(f"保存 {len(documents)} 条收益数据")
        except Exception as e:
            logger.error(f"保存收益数据失败: {e}")
            import traceback
            traceback.print_exc()

    def save_draw(self, chart_data):
        """保存自定义图表数据
        
        注意：图表数据暂时跳过，因为这不是核心业务数据
        如果需要，可以在 SQLite 中添加 panda_custom_chart 表
        """
        logger.debug("自定义图表数据暂不保存到 SQLite")
        pass

    def _run_async(self, coro):
        """在同步上下文中运行异步函数"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 如果事件循环正在运行，创建新的线程来运行
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, coro)
                    future.result()
            else:
                # 如果事件循环未运行，直接运行
                loop.run_until_complete(coro)
        except RuntimeError:
            # 如果没有事件循环，创建一个新的
            asyncio.run(coro)


# 为了向后兼容，保持相同的类名
ResultDb = ResultSQLite

