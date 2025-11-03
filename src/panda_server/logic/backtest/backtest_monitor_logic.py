"""
回测实时监控逻辑
提供实时监控数据接口，综合获取账户、交易、持仓、收益的最新数据和统计信息
"""
import logging
from typing import Dict, Any, List
from panda_server.dao.backtest_dao import (
    BacktestAccountDAO,
    BacktestTradeDAO,
    BacktestPositionDAO,
    BacktestProfitDAO,
    BacktestDAO
)

logger = logging.getLogger(__name__)


async def get_monitor_data(back_id: str) -> Dict[str, Any]:
    """
    获取回测的实时监控数据
    
    Args:
        back_id: 回测ID
        
    Returns:
        dict: 包含统计、最新账户、最新持仓、最近交易等信息
    """
    try:
        # 1. 获取数据统计
        account_count = await BacktestAccountDAO.count_by_back_id(back_id)
        trade_count = await BacktestTradeDAO.count_by_back_id(back_id)
        position_count = await BacktestPositionDAO.count_by_back_id(back_id)
        profit_count = await BacktestProfitDAO.count_by_back_id(back_id)
        
        # 2. 获取最新账户数据（最近1条）
        latest_account = None
        account_list, _ = await BacktestAccountDAO.list_by_back_id(back_id, page=1, page_size=999999)
        if account_list:
            # 按日期排序，获取最新的
            sorted_accounts = sorted(account_list, key=lambda x: x.get('date', ''), reverse=True)
            if sorted_accounts:
                account = sorted_accounts[0]
                # 计算收益率（如果有初始资金）
                initial_capital = None
                if len(account_list) > 0:
                    first_account = sorted(account_list, key=lambda x: x.get('date', ''))[0]
                    initial_capital = first_account.get('total_value')
                
                profit_rate = None
                if initial_capital and initial_capital > 0:
                    current_value = account.get('total_value', 0) or 0
                    profit_rate = (current_value - initial_capital) / initial_capital
                
                latest_account = {
                    'date': account.get('date'),
                    'total_asset': account.get('total_value'),
                    'available': account.get('available') or account.get('cash') or account.get('balance'),
                    'market_value': account.get('market_value'),
                    'profit': account.get('position_profit'),
                    'profit_rate': profit_rate,
                }
        
        # 3. 获取最近5笔交易
        recent_trades = []
        trade_list, _ = await BacktestTradeDAO.list_by_back_id(back_id, page=1, page_size=999999)
        if trade_list:
            # 按日期和时间排序
            sorted_trades = sorted(
                trade_list,
                key=lambda x: (x.get('date', ''), x.get('time', '')),
                reverse=True
            )[:5]
            
            for trade in sorted_trades:
                # direction 转换：0 (SIDE_BUY) -> "买入", 1 (SIDE_SELL) -> "卖出"
                direction = trade.get('direction')
                direction_text = "买入"
                if direction == 1 or direction == "1":
                    direction_text = "卖出"
                elif direction == 0 or direction == "0":
                    direction_text = "买入"
                
                # 计算amount（如果没有）
                amount = trade.get('amount')
                if amount is None:
                    price = trade.get('price', 0) or 0
                    volume = trade.get('volume', 0) or 0
                    amount = float(price) * float(volume) if price and volume else 0
                
                recent_trades.append({
                    'date': trade.get('date'),
                    'time': trade.get('time'),
                    'symbol': trade.get('symbol'),
                    'side': direction,
                    'direction': direction_text,
                    'price': trade.get('price'),
                    'volume': trade.get('volume'),
                    'amount': amount,
                })
        
        # 4. 获取最新日期的持仓（按日期分组，取最新日期的所有持仓）
        latest_positions = []
        position_list, _ = await BacktestPositionDAO.list_by_back_id(back_id, page=1, page_size=999999)
        if position_list:
            # 找出最新日期
            dates = [p.get('date', '') for p in position_list if p.get('date')]
            if dates:
                latest_date = max(dates)
                # 获取最新日期的所有持仓
                positions_on_date = [p for p in position_list if p.get('date') == latest_date]
                
                for pos in positions_on_date:
                    latest_positions.append({
                        'date': pos.get('date'),
                        'symbol': pos.get('symbol'),
                        'volume': pos.get('volume'),
                        'market_value': pos.get('market_value'),
                        'profit': pos.get('profit'),
                        'profit_rate': pos.get('profit_rate'),
                    })
        
        # 5. 获取净值曲线数据（最近50个数据点）
        equity_curve = []
        if account_list:
            sorted_accounts = sorted(account_list, key=lambda x: x.get('date', ''))
            recent_accounts = sorted_accounts[-50:] if len(sorted_accounts) > 50 else sorted_accounts
            
            for acc in recent_accounts:
                total_value = acc.get('total_value')
                if total_value is not None:
                    equity_curve.append({
                        'date': acc.get('date'),
                        'value': total_value,
                    })
        
        # 6. 获取回测基本信息
        backtest_info = await BacktestDAO.get_by_run_id(back_id)
        status = 'unknown'
        progress = 0
        if backtest_info:
            status = backtest_info.get('status', 'unknown')
            progress = backtest_info.get('progress', 0)
        
        # 组装返回数据
        return {
            'success': True,
            'back_id': back_id,
            'status': status,
            'progress': progress,
            'stats': {
                'account_count': account_count,
                'trade_count': trade_count,
                'position_count': position_count,
                'profit_count': profit_count,
            },
            'latest_account': latest_account,
            'recent_trades': recent_trades,
            'latest_positions': latest_positions,
            'equity_curve': equity_curve,
        }
        
    except Exception as e:
        logger.error(f"获取监控数据失败: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e),
            'back_id': back_id,
        }

