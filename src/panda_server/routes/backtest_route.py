from fastapi import APIRouter, HTTPException, status, Query
from typing import Optional
import traceback
import logging

from panda_server.logic.backtest.backtest_backtest_get_logic import backtest_backtest_get_logic
from panda_server.logic.backtest.backtest_account_get_logic import backtest_account_get_logic
from panda_server.logic.backtest.backtest_position_get_logic import backtest_position_get_logic
from panda_server.logic.backtest.backtest_profit_get_logic import backtest_profit_get_logic
from panda_server.logic.backtest.backtest_trade_get_logic import backtest_trade_get_logic
from panda_server.logic.backtest.backtest_user_strategy_log_get_logic import backtest_user_strategy_log_get_logic
from panda_server.logic.backtest.backtest_start_logic import start_backtest, get_backtest_progress
from panda_server.logic.backtest.backtest_delete_logic import delete_backtest, batch_delete_backtests
from panda_server.logic.backtest.backtest_list_get_logic import backtest_list_get_logic
from panda_server.models.backtest.query_backtest_response import QueryBacktestBacktestResponse
from panda_server.models.backtest.query_account_response import QueryBacktestAccountListResponse
from panda_server.models.backtest.query_position_response import QueryBacktestPositionListResponse
from panda_server.models.backtest.query_profit_response import QueryBacktestProfitListResponse
from panda_server.models.backtest.query_trade_response import QueryBacktestTradeListResponse
from panda_server.models.backtest.query_user_strategy_log_response import QueryBacktestUserStrategyLogListResponse
from panda_server.models.backtest.backtest_start_request import BacktestStartRequest, BacktestStartResponse

# 获取 logger
logger = logging.getLogger(__name__)

# 创建路由实例，设置前缀和标签
router = APIRouter(
    prefix="/api/backtest",
    tags=["backtest"]
)

@router.get("/list")
async def get_backtest_list(
    page: int = Query(1, description="页码", ge=1),
    page_size: int = Query(20, description="每页数量", ge=1, le=100),
    status: Optional[str] = Query(None, description="状态筛选: running, completed, failed")
):
    """
    获取回测列表，支持分页和状态筛选
    """
    try:
        return await backtest_list_get_logic(page, page_size, status)
    except Exception as e:
        stack_trace = traceback.format_exc()
        logger.error(f"Unexpected error in get_backtest_list: {e}\n{stack_trace}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取回测列表失败: {str(e)}",
        )


@router.get(
    "/backtest", response_model=QueryBacktestBacktestResponse,status_code=status.HTTP_200_OK)
async def get_backtest(
    back_id: str = Query(..., description="回测ID")
) -> QueryBacktestBacktestResponse:
    """
    根据回测ID获取回测结果
    Args:
        back_id: 回测ID (查询参数)
    Returns:
        回测结果详细信息，如果ID不存在则返回错误
    """
    try:
        return await backtest_backtest_get_logic(back_id)
    except HTTPException:
        raise
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid backtest id format: {back_id}",
        )
    except Exception as e:
        stack_trace = traceback.format_exc()
        logger.error(f"Unexpected error in get_backtest_by_id: {e}\n{stack_trace}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while retrieving the backtest result",
        )


@router.get("/account", response_model=QueryBacktestAccountListResponse,status_code=status.HTTP_200_OK)
async def get_backtest_account(
    back_id: str = Query(..., description="回测ID"),
    page: int = 1,
    page_size: int = 10
) -> QueryBacktestAccountListResponse:
    """
    根据回测ID获取回测账户信息，支持分页
    Args:
        back_id: 回测ID (查询参数)
        page: 当前页码，默认为1
        page_size: 每页数据条数，默认为10
    Returns:
        回测账户信息列表及分页信息
    """
    try:
        return await backtest_account_get_logic(back_id, page, page_size)
    except HTTPException:
        raise
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid backtest id format: {back_id}",
        )
    except Exception as e:
        stack_trace = traceback.format_exc()
        logger.error(f"Unexpected error in get_backtest_account: {e}\n{stack_trace}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while retrieving the backtest account result",
        )


@router.get("/position", response_model=QueryBacktestPositionListResponse, status_code=status.HTTP_200_OK)
async def get_backtest_positions(
    back_id: str = Query(..., description="回测ID"),
    page: int = 1,
    page_size: int = 10,
    date: Optional[str] = None
) -> QueryBacktestPositionListResponse:
    """
    根据回测ID获取回测持仓信息，支持分页
    Args:
        back_id: 回测ID (查询参数)
        page: 当前页码，默认为1
        page_size: 每页数据条数，默认为10
        date: 可选的日期参数，格式为 "YYYY-MM-DD"
    Returns:
        回测持仓信息列表及分页信息
    """
    try:
        return await backtest_position_get_logic(back_id, page, page_size, date)
    except HTTPException:
        raise
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid backtest id format: {back_id}",
        )
    except Exception as e:
        stack_trace = traceback.format_exc()
        logger.error(f"Unexpected error in get_backtest_positions: {e}\n{stack_trace}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while retrieving the backtest position result",
        )

@router.get("/profit", response_model=QueryBacktestProfitListResponse, status_code=status.HTTP_200_OK)
async def get_backtest_profits(
    back_id: str = Query(..., description="回测ID"),
    page: int = 1,
    page_size: int = 10
) -> QueryBacktestProfitListResponse:
    """
    根据回测ID获取回测收益信息，支持分页
    Args:
        back_id: 回测ID (查询参数)
        page: 当前页码，默认为1
        page_size: 每页数据条数，默认为10
    Returns:
        回测收益信息列表及分页信息
    """
    try:
        return await backtest_profit_get_logic(back_id, page, page_size)
    except HTTPException:
        raise
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid backtest id format: {back_id}",
        )
    except Exception as e:
        stack_trace = traceback.format_exc()
        logger.error(f"Unexpected error in get_backtest_profits: {e}\n{stack_trace}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while retrieving the backtest profit result",
        )

@router.get("/trade", response_model=QueryBacktestTradeListResponse, status_code=status.HTTP_200_OK)
async def get_backtest_trade(
    back_id: str = Query(..., description="回测ID"),
    page: int = 1,
    page_size: int = 10
) -> QueryBacktestTradeListResponse:
    """
    根据回测ID获取回测交易信息，支持分页
    Args:
        back_id: 回测ID (查询参数)
        page: 当前页码，默认为1
        page_size: 每页数据条数，默认为10
    Returns:
        回测交易信息列表及分页信息
    """
    try:
        return await backtest_trade_get_logic(back_id, page, page_size)
    except HTTPException:
        raise
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid backtest id format: {back_id}",
        )
    except Exception as e:
        stack_trace = traceback.format_exc()
        logger.error(f"Unexpected error in get_backtest_trade: {e}\n{stack_trace}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while retrieving the backtest trade result",
        )

@router.get("/userstrategylog", response_model=QueryBacktestUserStrategyLogListResponse)
async def get_user_strategy_logs(
    relation_id: str,
    last_sort: int = None,
    limit: int = 20
) -> QueryBacktestUserStrategyLogListResponse:
    """
    根据 relation_id 获取 panda_user_strategy_log 记录，支持基于 sort 字段的游标式分页，并返回游标信息
    """
    try:
        return await backtest_user_strategy_log_get_logic(relation_id, last_sort, limit)
    except HTTPException:
        raise
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid relation_id format: {relation_id}",
        )
    except Exception as e:
        stack_trace = traceback.format_exc()
        logger.error(f"Unexpected error in get_user_strategy_logs: {e}\n{stack_trace}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while retrieving the user strategy log result",
        )


@router.post("/start", response_model=BacktestStartResponse)
async def start_backtest_route(request: BacktestStartRequest) -> BacktestStartResponse:
    """
    启动回测
    """
    try:
        return await start_backtest(request)
    except Exception as e:
        stack_trace = traceback.format_exc()
        logger.error(f"Unexpected error in start_backtest: {e}\n{stack_trace}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"启动回测失败: {str(e)}",
        )


@router.get("/progress")
async def get_backtest_progress_route(
    back_id: str = Query(..., description="回测ID")
):
    """
    获取回测进度
    """
    try:
        return await get_backtest_progress(back_id)
    except Exception as e:
        stack_trace = traceback.format_exc()
        logger.error(f"Unexpected error in get_backtest_progress: {e}\n{stack_trace}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取回测进度失败: {str(e)}",
        )


@router.delete("/delete")
async def delete_backtest_route(
    back_id: str = Query(..., description="回测ID")
):
    """
    删除回测及其所有相关数据
    """
    try:
        result = await delete_backtest(back_id)
        if result["success"]:
            return result
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["message"]
            )
    except HTTPException:
        raise
    except Exception as e:
        stack_trace = traceback.format_exc()
        logger.error(f"Unexpected error in delete_backtest: {e}\n{stack_trace}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除回测失败: {str(e)}",
        )


@router.post("/batch_delete")
async def batch_delete_backtests_route(
    back_ids: list = Query(..., description="回测ID列表")
):
    """
    批量删除回测
    """
    try:
        result = await batch_delete_backtests(back_ids)
        return result
    except Exception as e:
        stack_trace = traceback.format_exc()
        logger.error(f"Unexpected error in batch_delete_backtests: {e}\n{stack_trace}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"批量删除回测失败: {str(e)}",
        ) 