"""回测删除逻辑"""
import logging
from panda_server.dao.backtest_dao import BacktestDAO

logger = logging.getLogger(__name__)


async def delete_backtest(back_id: str) -> dict:
    """删除回测及其所有相关数据
    
    Args:
        back_id: 回测ID
        
    Returns:
        删除结果
    """
    try:
        # 使用 SQLite DAO 删除回测（会自动级联删除相关数据）
        deleted = await BacktestDAO.delete(back_id)
        
        if deleted:
            logger.info(f"成功删除回测 {back_id}")
            return {
                "success": True,
                "message": "删除成功",
                "data": {
                    "back_id": back_id
                }
            }
        else:
            return {
                "success": False,
                "message": f"回测不存在: {back_id}",
                "data": {}
            }
        
    except Exception as e:
        logger.error(f"删除回测失败: {str(e)}")
        return {
            "success": False,
            "message": f"删除失败: {str(e)}",
            "data": {}
        }


async def batch_delete_backtests(back_ids: list) -> dict:
    """批量删除回测
    
    Args:
        back_ids: 回测ID列表
        
    Returns:
        批量删除结果
    """
    try:
        # 使用 SQLite DAO 批量删除
        deleted_count = await BacktestDAO.batch_delete(back_ids)
        
        return {
            "success": True,
            "message": f"批量删除完成: 成功删除 {deleted_count} 条记录",
            "data": {
                "deleted_count": deleted_count
            }
        }
    except Exception as e:
        logger.error(f"批量删除回测失败: {str(e)}")
        return {
            "success": False,
            "message": f"批量删除失败: {str(e)}",
            "data": {}
        }

