"""策略管理逻辑"""
import logging
from fastapi import HTTPException, status
from datetime import datetime
from panda_server.dao.strategy_dao import StrategyDAO
from panda_server.models.strategy.strategy_model import (
    StrategyModel,
    CreateStrategyRequest,
    UpdateStrategyRequest,
    StrategyResponse,
    StrategyListResponse
)

logger = logging.getLogger(__name__)


async def create_strategy(request: CreateStrategyRequest) -> StrategyResponse:
    """创建策略"""
    try:
        # 使用 SQLite DAO 创建策略
        strategy_data = await StrategyDAO.create(
            name=request.name,
            code=request.code,
            description=request.description
        )
        
        # DAO 层已经将 _id 转换为字符串格式
        return StrategyResponse(
            success=True,
            message="策略创建成功",
            data=StrategyModel(**strategy_data)
        )
    except Exception as e:
        logger.error(f"创建策略失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建策略失败: {str(e)}"
        )


async def get_strategy(strategy_id: str) -> StrategyResponse:
    """获取策略详情"""
    try:
        # 使用 SQLite DAO 获取策略
        result = await StrategyDAO.get_by_id(int(strategy_id))
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"策略不存在: {strategy_id}"
            )
        
        # DAO 层已经将 _id 转换为字符串格式
        return StrategyResponse(
            success=True,
            message="获取成功",
            data=StrategyModel(**result)
        )
    except HTTPException:
        raise
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效的策略ID: {strategy_id}"
        )
    except Exception as e:
        logger.error(f"获取策略失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取策略失败: {str(e)}"
        )


async def list_strategies(page: int = 1, page_size: int = 20) -> StrategyListResponse:
    """获取策略列表"""
    try:
        # 使用 SQLite DAO 获取策略列表
        strategies_data, total = await StrategyDAO.list_all(page, page_size)
        
        strategies = []
        for doc in strategies_data:
            # DAO 层已经将 _id 转换为字符串格式
            strategies.append(StrategyModel(**doc))
        
        return StrategyListResponse(
            success=True,
            message="获取成功",
            data=strategies,
            total=total
        )
    except Exception as e:
        logger.error(f"获取策略列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取策略列表失败: {str(e)}"
        )


async def update_strategy(strategy_id: str, request: UpdateStrategyRequest) -> StrategyResponse:
    """更新策略"""
    try:
        # 使用 SQLite DAO 更新策略
        result = await StrategyDAO.update(
            strategy_id=int(strategy_id),
            name=request.name,
            code=request.code,
            description=request.description
        )
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"策略不存在: {strategy_id}"
            )
        
        # DAO 层已经将 _id 转换为字符串格式
        return StrategyResponse(
            success=True,
            message="更新成功",
            data=StrategyModel(**result)
        )
    except HTTPException:
        raise
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效的策略ID: {strategy_id}"
        )
    except Exception as e:
        logger.error(f"更新策略失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新策略失败: {str(e)}"
        )


async def delete_strategy(strategy_id: str) -> StrategyResponse:
    """删除策略"""
    try:
        # 使用 SQLite DAO 删除策略
        deleted = await StrategyDAO.delete(int(strategy_id))
        
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"策略不存在: {strategy_id}"
            )
        
        return StrategyResponse(
            success=True,
            message="删除成功",
            data=None
        )
    except HTTPException:
        raise
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效的策略ID: {strategy_id}"
        )
    except Exception as e:
        logger.error(f"删除策略失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除策略失败: {str(e)}"
        )

