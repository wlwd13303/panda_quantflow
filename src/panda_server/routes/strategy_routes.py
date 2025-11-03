"""策略管理路由"""
from fastapi import APIRouter, Query
from panda_server.logic.strategy.strategy_logic import (
    create_strategy,
    get_strategy,
    list_strategies,
    update_strategy,
    delete_strategy
)
from panda_server.models.strategy.strategy_model import (
    CreateStrategyRequest,
    UpdateStrategyRequest,
    StrategyResponse,
    StrategyListResponse
)

router = APIRouter(
    prefix="/api/strategy",
    tags=["strategy"]
)


@router.post("/", response_model=StrategyResponse)
async def create_strategy_route(request: CreateStrategyRequest):
    """创建策略"""
    return await create_strategy(request)


@router.get("/{strategy_id}", response_model=StrategyResponse)
async def get_strategy_route(strategy_id: str):
    """获取策略详情"""
    return await get_strategy(strategy_id)


@router.get("/", response_model=StrategyListResponse)
async def list_strategies_route(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量")
):
    """获取策略列表"""
    return await list_strategies(page, page_size)


@router.put("/{strategy_id}", response_model=StrategyResponse)
async def update_strategy_route(strategy_id: str, request: UpdateStrategyRequest):
    """更新策略"""
    return await update_strategy(strategy_id, request)


@router.delete("/{strategy_id}", response_model=StrategyResponse)
async def delete_strategy_route(strategy_id: str):
    """删除策略"""
    return await delete_strategy(strategy_id)

