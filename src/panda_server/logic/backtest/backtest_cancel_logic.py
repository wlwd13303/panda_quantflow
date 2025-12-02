"""回测终止逻辑"""
import logging
from datetime import datetime
from panda_server.dao.backtest_dao import BacktestDAO

logger = logging.getLogger(__name__)


async def cancel_backtest(back_test_id: str) -> dict:
    """终止正在运行的回测
    
    Args:
        back_test_id: 回测ID
        
    Returns:
        操作结果
    """
    try:
        # 1. 获取回测信息
        backtest = await BacktestDAO.get_by_run_id(back_test_id)
        
        if not backtest:
            return {
                "success": False,
                "message": f"回测不存在: {back_test_id}"
            }
        
        # 2. 检查回测状态
        current_status = backtest.get('status', 'unknown')
        
        if current_status == 'completed':
            return {
                "success": False,
                "message": "回测已完成，无法终止"
            }
        
        if current_status == 'failed':
            return {
                "success": False,
                "message": "回测已失败，无需终止"
            }
        
        if current_status == 'cancelled':
            return {
                "success": False,
                "message": "回测已被终止"
            }
        
        # 3. 更新回测状态为 cancelled
        await BacktestDAO.update(
            run_id=back_test_id,
            status="cancelled",
            error_message="用户手动终止",
            completed_at=datetime.now()
        )
        
        logger.info(f"回测已标记为终止: {back_test_id}")
        
        return {
            "success": True,
            "message": "回测终止请求已发送，回测将在下一个检查点停止",
            "back_test_id": back_test_id
        }
        
    except Exception as e:
        logger.error(f"终止回测失败 {back_test_id}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "success": False,
            "message": f"终止回测失败: {str(e)}"
        }

