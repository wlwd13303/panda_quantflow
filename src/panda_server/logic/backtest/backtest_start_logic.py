"""回测启动逻辑"""
import logging
import os
import tempfile
import asyncio
from bson import ObjectId
from datetime import datetime
from panda_server.config.database import mongodb
from panda_server.dao.backtest_dao import BacktestDAO
from panda_server.models.backtest.backtest_start_request import (
    BacktestStartRequest,
    BacktestStartResponse
)

logger = logging.getLogger(__name__)

COLLECTION_NAME = "panda_back_test"


async def start_backtest(request: BacktestStartRequest) -> BacktestStartResponse:
    """启动回测
    
    Args:
        request: 回测启动请求
        
    Returns:
        回测启动响应，包含回测ID
    """
    try:
        # 1. 生成回测ID
        back_test_id = str(ObjectId())
        
        # 2. 创建临时策略文件
        temp_dir = tempfile.gettempdir()
        strategy_file = os.path.join(temp_dir, f"strategy_{back_test_id}.py")
        
        with open(strategy_file, 'w', encoding='utf-8') as f:
            f.write(request.strategy_code)
        
        # 3. 初始化回测记录
        backtest_record = {
            "_id": ObjectId(back_test_id),
            "strategy_name": request.strategy_name,
            "start_date": request.start_date,
            "end_date": request.end_date,
            "start_capital": request.start_capital,
            "status": "running",  # running, completed, failed
            "progress": 0,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
        
        collection = mongodb.get_collection(COLLECTION_NAME)
        await collection.insert_one(backtest_record)
        
        # 4. 构建回测参数
        handle_message = {
            'file': strategy_file,
            'start_date': request.start_date,
            'end_date': request.end_date,
            'start_capital': request.start_capital,
            'account_id': request.account_id,
            'account_type': request.account_type,
            'commission_rate': request.commission_rate,
            'slippage': request.slippage,
            'frequency': request.frequency,
            'matching_type': request.matching_type,
            'standard_symbol': request.standard_symbol,
            'run_type': 1,
            'back_test_id': back_test_id,
            'mock_id': '100',
            'run_params': '[]',
            'margin_rate': request.margin_rate,
            'start_future_capital': request.start_future_capital,
            'start_fund_capital': request.start_fund_capital,
        }
        
        # 5. 异步启动回测（不阻塞API响应）
        asyncio.create_task(_run_backtest_async(handle_message, strategy_file))
        
        return BacktestStartResponse(
            success=True,
            message="回测已启动，正在运行中...",
            back_test_id=back_test_id,
            data={
                "back_test_id": back_test_id,
                "status": "running",
                "strategy_name": request.strategy_name
            }
        )
        
    except Exception as e:
        logger.error(f"启动回测失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return BacktestStartResponse(
            success=False,
            message=f"启动回测失败: {str(e)}",
            data={}
        )


async def _run_backtest_async(handle_message: dict, strategy_file: str):
    """异步运行回测
    
    Args:
        handle_message: 回测参数
        strategy_file: 策略文件路径
    """
    back_test_id = handle_message['back_test_id']
    collection = mongodb.get_collection(COLLECTION_NAME)
    
    try:
        logger.info(f"开始执行回测: {back_test_id}")
        
        # 使用线程池执行同步的回测代码
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _run_backtest_sync, handle_message)
        
        # 更新回测状态为完成
        await collection.update_one(
            {"_id": ObjectId(back_test_id)},
            {"$set": {
                "status": "completed",
                "progress": 100,
                "updated_at": datetime.now()
            }}
        )
        
        logger.info(f"回测完成: {back_test_id}")
        
    except Exception as e:
        logger.error(f"回测执行失败 {back_test_id}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
        # 更新回测状态为失败
        await collection.update_one(
            {"_id": ObjectId(back_test_id)},
            {"$set": {
                "status": "failed",
                "error": str(e),
                "updated_at": datetime.now()
            }}
        )
    finally:
        # 清理临时策略文件
        try:
            if os.path.exists(strategy_file):
                os.remove(strategy_file)
                logger.info(f"已清理临时策略文件: {strategy_file}")
        except Exception as e:
            logger.warning(f"清理临时文件失败: {e}")


def _run_backtest_sync(handle_message: dict):
    """同步运行回测（在线程池中执行）
    
    Args:
        handle_message: 回测参数
    """
    from panda_backtest.main_local import Run
    
    logger.info(f"启动回测引擎: {handle_message['back_test_id']}")
    Run.start(handle_message)
    logger.info(f"回测引擎执行完成: {handle_message['back_test_id']}")


async def get_backtest_progress(back_test_id: str) -> dict:
    """获取回测进度
    
    Args:
        back_test_id: 回测ID (可能是 run_id 或整数 ID)
        
    Returns:
        回测进度信息
    """
    try:
        # 首先尝试通过 run_id 查询
        result = await BacktestDAO.get_by_run_id(back_test_id)
        
        # 如果通过 run_id 查询不到，尝试通过整数 ID 查询（兼容前端传入的整数ID）
        if not result:
            result = await BacktestDAO.get_by_id(back_test_id)
        
        if not result:
            return {
                "success": False,
                "message": "回测不存在",
                "data": {}
            }
        
        return {
            "success": True,
            "message": "获取成功",
            "data": {
                "back_test_id": back_test_id,
                "status": result.get("status", "unknown"),
                "progress": result.get("progress", 0),
                "error": result.get("error_message")  # SQLite 使用 error_message 字段
            }
        }
    except Exception as e:
        logger.error(f"获取回测进度失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "success": False,
            "message": f"获取回测进度失败: {str(e)}",
            "data": {}
        }

