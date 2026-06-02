from common.connector.mongodb_handler import DatabaseHandler
from panda_backtest.api.api import *
import datetime
import panda_data
from panda_factor.generate.macro_factor import MacroFactor
from common.config.config import config
from utils.data.data_util import DateUtil


class IndexConstituentsMapper:
    """指数成分股映射器，支持缓存和快速查询"""

    def __init__(self):
        self._constituents_cache = {}  # 缓存不同指数的成分股
        self._last_update = {}  # 记录最后更新时间

    def get_constituents(self, index_code, force_refresh=False):
        """获取指数成分股，带缓存机制"""
        current_date = datetime.datetime.now().strftime('%Y%m%d')

        # 检查是否需要更新缓存
        if not force_refresh and index_code in self._constituents_cache:
            last_update = self._last_update.get(index_code, '')
            if last_update == current_date:
                SRLogger.info(f"使用缓存的 {index_code} 指数成分股数据")
                return self._constituents_cache[index_code]

        # 从数据源获取最新成分股
        constituents = self._fetch_constituents(index_code)

        # 更新缓存
        self._constituents_cache[index_code] = constituents
        self._last_update[index_code] = current_date

        SRLogger.info(f"更新 {index_code} 指数成分股缓存，获取到 {len(constituents)} 只股票")
        return constituents

    def _fetch_constituents(self, index_code):
        """从数据源获取成分股"""
        try:
            # 使用panda_data获取最近一个月的数据来提取成分股
            end_date = datetime.datetime.now().strftime('%Y%m%d')
            start_date = (datetime.datetime.now() - datetime.timedelta(days=30)).strftime('%Y%m%d')

            market_df = panda_data.get_market_data(
                start_date=start_date,
                end_date=end_date,
                indicator=index_code
            )

            if not market_df.empty:
                return market_df['symbol'].unique().tolist()
            else:
                SRLogger.warning(f"无法获取 {index_code} 指数成分股数据")
                return []

        except Exception as e:
            SRLogger.error(f"获取 {index_code} 成分股失败: {str(e)}")
            return []


class StockPoolManager:
    """股票池管理器"""

    def __init__(self):
        self.index_mapper = IndexConstituentsMapper()

    def get_stock_pool(self, pool_type='index', **kwargs):
        """获取不同类型的股票池"""
        if pool_type == 'index':
            index_code = kwargs.get('index_code', '000300')
            return self.index_mapper.get_constituents(index_code)
        elif pool_type == 'all_stocks':
            return panda_data.get_all_symbols()
        elif pool_type == 'custom':
            return kwargs.get('symbols', [])
        else:
            raise ValueError(f"不支持的股票池类型: {pool_type}")


def initialize(context):
    """策略初始化"""
    SRLogger.info("=== 突破策略初始化（全市场多股票版） ===")

    panda_data.init()
    macro_factor = MacroFactor()

    # ========== 基础配置 ==========
    context.account = '8888'

    # ========== 策略参数 ==========
    context.max_positions = 10  # 最大持仓股票数量
    context.last_strategy_execution_date = None  # 上次执行策略的日期
    context.previous_date = None
    # ========== 股票池配置 ==========
    # 创建股票池管理器
    pool_manager = StockPoolManager()

    # 获取沪深300指数成分股作为股票池
    try:
        context.stock_pool = pool_manager.get_stock_pool(index_code='000300')

        # 如果获取失败或为空，使用默认测试股票池
        if not context.stock_pool:
            SRLogger.warning("无法获取沪深300成分股，使用默认测试股票池")
            context.stock_pool = ['002317.SZ']

    except Exception as e:
        SRLogger.error(f"获取股票池失败: {str(e)}，使用默认测试股票池")
        context.stock_pool = ['002317.SZ']

    SRLogger.info(f"股票池初始化完成，共 {len(context.stock_pool)} 只股票")


def get_current_position_size(context, stock_id):
    """获取当前持仓数量"""
    try:
        account = context.stock_account_dict.get(context.account)
        if account and hasattr(account, 'positions'):
            position = account.positions.get(stock_id)
            if position and hasattr(position, 'quantity'):
                return position.quantity
            if hasattr(account, 'position_dict'):
                position = account.position_dict.get(stock_id)
                if position:
                    return position.today_amount + position.enable_amount
        return 0
    except Exception as e:
        return 0


def get_current_positions_count(context):
    """获取当前持仓股票数量"""
    try:
        account = context.stock_account_dict.get(context.account)
        if account and hasattr(account, 'positions'):
            return len([p for p in account.positions.values() if p.quantity > 0])
        return 0
    except Exception as e:
        return 0



def should_execute_strategy_today(context, current_date):
    """判断今天是否应该执行策略（每周第一个交易日）"""
    try:
        # 获取当前是星期几 (0=周一, 1=周二, ..., 6=周日)
        current_dt = datetime.datetime.strptime(current_date, '%Y%m%d')
        if current_dt.weekday() == 0:
            return True

        # 如果是第一次执行，执行策略
        if context.last_strategy_execution_date is None:
            return True

        # 计算当前日期和上次执行日期的天数差
        last_dt = datetime.datetime.strptime(context.last_strategy_execution_date, '%Y%m%d')
        days_diff = (current_dt - last_dt).days

        # 如果相差4天以上（考虑到周末和节假日），认为是新的一周，应该执行
        if days_diff >= 4:
            return True

        return False
    except Exception as e:
        SRLogger.error(f"判断执行日期失败: {str(e)}")
        # 出错时保守起见，执行策略
        return True


def handle_data(context, bar_dict):
    """每个Bar的处理逻辑"""
    current_date = context.now

    # 判断今天是否应该执行策略（每周第一个交易日）
    if not should_execute_strategy_today(context, current_date):
        SRLogger.info(f"[{current_date}] 非每周第一个交易日，跳过策略执行")
        return

    # 更新上次执行日期
    context.last_strategy_execution_date = current_date
    SRLogger.info(f"[{current_date}] 每周第一个交易日，开始执行策略")

    # 从股票池中过滤出有数据的股票
    # 使用 'stock_id in bar_dict' 来判断该股票是否有当前bar数据
    available_stocks = [stock_id for stock_id in context.stock_pool if stock_id in bar_dict]


def before_trading(context):
    """盘前处理"""
    try:


        account = context.stock_account_dict[context.account]
        positions_count = get_current_positions_count(context)

        # 统计窗口期股票数量
        stage1_count = sum(1 for s in context.stock_states.values() if s.in_sar_window)
        stage2_count = sum(1 for s in context.stock_states.values() if s.in_surge_window)

        SRLogger.info(f"[{context.now}] 开盘前 - 账户总资产：{account.total_value:.2f}, "
                      f"可用资金：{account.cash:.2f}, 持仓股票数：{positions_count}/{context.max_positions}")

        # check_out_list = get_stock_list(context)

    except Exception as e:
        SRLogger.error(f"盘前处理失败: {str(e)}")


def after_trading(context):
    """盘后处理"""
    try:
        account = context.stock_account_dict[context.account]
        positions_count = get_current_positions_count(context)

        SRLogger.info(f"[{context.now}] 收盘后统计：")
        SRLogger.info(f"  - 账户总资产：{account.total_value:.2f}")
        SRLogger.info(f"  - 持仓市值：{account.market_value:.2f}")
        SRLogger.info(f"  - 可用资金：{account.cash:.2f}")
        SRLogger.info(f"  - 持仓股票数：{positions_count}")

        # 显示持仓详情
        if positions_count > 0:
            SRLogger.info(f"  持仓明细：")
            for stock_id, state in context.stock_states.items():
                if state.position_held and state.entry_price:
                    position_size = get_current_position_size(context, stock_id)
                    if position_size > 0 and len(state.price_history) > 0:
                        current_price = state.price_history[-1]['close']
                        profit_ratio = (current_price - state.entry_price) / state.entry_price * 100
                        SRLogger.info(f"    [{stock_id}] 数量={position_size}, "
                                      f"成本={state.entry_price:.2f}, "
                                      f"现价={current_price:.2f}, "
                                      f"盈亏={profit_ratio:+.2f}%")

    except Exception as e:
        SRLogger.error(f"盘后处理失败: {str(e)}")


def on_stock_trade_rtn(context, order, bar_dict):
    """股票交易回报"""
    try:
        side_text = '买入' if order.side == 1 else '卖出'
        SRLogger.info(
            f"✅ 交易回报 - {order.order_book_id}: {side_text} {order.filled_quantity}股 @ {order.avg_price:.2f}元")
    except Exception as e:
        SRLogger.error(f"交易回报处理失败: {str(e)}")


def stock_order_cancel(context, order, bar_dict):
    """股票订单撤销回报"""
    try:
        SRLogger.info(f"订单撤销 - {order.order_book_id}: {order.quantity}股订单被撤销")
    except Exception as e:
        SRLogger.error(f"订单撤销处理失败: {str(e)}")
