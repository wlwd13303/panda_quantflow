"""
Backtest monitor logic.
Provides a bounded payload to avoid large SQLite reads and huge JSON responses.
"""
import logging
from typing import Dict, Any

from panda_server.dao.backtest_dao import (
    BacktestAccountDAO,
    BacktestTradeDAO,
    BacktestPositionDAO,
    BacktestProfitDAO,
    BacktestDAO,
)

logger = logging.getLogger(__name__)


async def get_monitor_data(back_id: str) -> Dict[str, Any]:
    """Get monitor data for a backtest with bounded result size."""
    try:
        max_recent_trades = 300
        max_latest_positions = 2000
        max_equity_points = 2000

        account_count = await BacktestAccountDAO.count_by_back_id(back_id)
        trade_count = await BacktestTradeDAO.count_by_back_id(back_id)
        position_count = await BacktestPositionDAO.count_by_back_id(back_id)
        profit_count = await BacktestProfitDAO.count_by_back_id(back_id)

        latest_account_row = await BacktestAccountDAO.get_latest_by_back_id(back_id)
        first_account_row = await BacktestAccountDAO.get_first_by_back_id(back_id)

        latest_account = None
        latest_total_value = None
        if latest_account_row:
            latest_total_value = latest_account_row.get("total_value")
            initial_total_value = first_account_row.get("total_value") if first_account_row else None

            profit_rate = None
            if initial_total_value not in (None, 0):
                try:
                    current_value = float(latest_total_value or 0)
                    initial_value = float(initial_total_value)
                    if initial_value > 0:
                        profit_rate = (current_value - initial_value) / initial_value
                except (TypeError, ValueError):
                    profit_rate = None

            latest_account = {
                "date": latest_account_row.get("date"),
                "total_asset": latest_total_value,
                "available": latest_account_row.get("available")
                or latest_account_row.get("cash")
                or latest_account_row.get("balance"),
                "market_value": latest_account_row.get("market_value"),
                "profit": latest_account_row.get("position_profit"),
                "profit_rate": profit_rate,
            }

        recent_trades = []
        trade_list = await BacktestTradeDAO.list_recent_by_back_id(
            back_id, limit=max_recent_trades
        )
        for trade in trade_list:
            direction = trade.get("direction")
            direction_text = "涔板叆"
            if direction == 1 or direction == "1":
                direction_text = "鍗栧嚭"
            elif direction == 0 or direction == "0":
                direction_text = "涔板叆"

            amount = trade.get("amount")
            if amount is None:
                price = trade.get("price", 0) or 0
                volume = trade.get("volume", 0) or 0
                amount = float(price) * float(volume) if price and volume else 0

            recent_trades.append(
                {
                    "date": trade.get("date"),
                    "time": trade.get("time"),
                    "symbol": trade.get("symbol"),
                    "contract_name": trade.get("contract_name"),
                    "side": direction,
                    "direction": direction_text,
                    "price": trade.get("price"),
                    "volume": trade.get("volume"),
                    "amount": amount,
                }
            )

        latest_positions = []
        position_list = await BacktestPositionDAO.list_latest_positions_by_back_id(
            back_id, limit=max_latest_positions
        )
        for pos in position_list:
            position_ratio = None
            market_value = pos.get("market_value") or 0
            if market_value and latest_total_value:
                try:
                    position_ratio = float(market_value) / float(latest_total_value)
                except Exception:
                    position_ratio = None

            latest_positions.append(
                {
                    "date": pos.get("date"),
                    "symbol": pos.get("symbol"),
                    "contract_name": pos.get("contract_name"),
                    "volume": pos.get("volume"),
                    "market_value": pos.get("market_value"),
                    "profit": pos.get("profit"),
                    "profit_rate": pos.get("profit_rate"),
                    "position_ratio": position_ratio,
                }
            )

        equity_curve = await BacktestAccountDAO.list_equity_curve_by_back_id(
            back_id, limit=max_equity_points
        )

        backtest_info = await BacktestDAO.get_by_run_id(back_id)
        status = "unknown"
        progress = 0
        if backtest_info:
            status = backtest_info.get("status", "unknown")
            progress = backtest_info.get("progress", 0)

        return {
            "success": True,
            "back_id": back_id,
            "status": status,
            "progress": progress,
            "stats": {
                "account_count": account_count,
                "trade_count": trade_count,
                "position_count": position_count,
                "profit_count": profit_count,
            },
            "latest_account": latest_account,
            "recent_trades": recent_trades,
            "latest_positions": latest_positions,
            "equity_curve": equity_curve,
            "payload_limits": {
                "recent_trades_limit": max_recent_trades,
                "latest_positions_limit": max_latest_positions,
                "equity_curve_limit": max_equity_points,
            },
        }

    except Exception as e:
        logger.error(f"鑾峰彇鐩戞帶鏁版嵁澶辫触: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "back_id": back_id,
        }

