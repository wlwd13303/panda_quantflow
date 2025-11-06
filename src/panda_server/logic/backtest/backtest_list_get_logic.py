"""回测列表查询逻辑"""
import logging
from panda_server.dao.backtest_dao import BacktestDAO

logger = logging.getLogger(__name__)


async def backtest_list_get_logic(page: int = 1, page_size: int = 20, status: str = None) -> dict:
    """获取回测列表
    
    Args:
        page: 页码
        page_size: 每页数量
        status: 状态筛选 (running, completed, failed)
        
    Returns:
        回测列表及分页信息
    """
    try:
        # 使用 SQLite DAO 获取回测列表
        items, total = await BacktestDAO.list_all(page, page_size, status)
        
        # 转换ID为字符串格式，并映射字段名
        for item in items:
            if "_id" in item:
                item["_id"] = str(item["_id"])
                # 如果没有run_id，用_id填充
                if "run_id" not in item:
                    item["run_id"] = item["_id"]
            
            # 将 strategy_code 字段映射为 strategy_code_snapshot
            # 因为在回测启动时，strategy_code 就是代码快照
            if "strategy_code" in item:
                item["strategy_code_snapshot"] = item["strategy_code"]
        
        return {
            "success": True,
            "code": 0,
            "message": "查询成功",
            "data": {
                "items": items,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size
            }
        }
        
    except Exception as e:
        logger.error(f"获取回测列表失败: {str(e)}")
        return {
            "success": False,
            "code": -1,
            "message": f"查询失败: {str(e)}",
            "data": {
                "items": [],
                "total": 0,
                "page": page,
                "page_size": page_size,
                "total_pages": 0
            }
        }

