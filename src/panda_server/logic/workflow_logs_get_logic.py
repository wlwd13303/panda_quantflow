import logging
from typing import Optional
from bson import ObjectId
from fastapi import HTTPException, status
from panda_server.config.database import mongodb
from common.logging.workflow_log import WorkflowLog, WorkflowLogRepository
from panda_server.models.query_logs_response import (
    QueryWorkflowLogsResponse,
    QueryWorkflowLogsResponseData,
)
from panda_server.models.workflow_run_model import WorkflowRunModel

logger = logging.getLogger(__name__)


async def workflow_logs_get_logic(
    user_id: str,
    workflow_run_id: str,
    work_node_id: Optional[str] = None,
    log_level: Optional[str] = None,
    last_sequence: Optional[int] = None,
    limit: int = 5,
) -> QueryWorkflowLogsResponse:
    """
    查询工作流日志业务逻辑

    支持特性：
    - 支持以 last_sequence 向后分页（获取更新的日志）
    - 支持 limit 分页查询，默认5条
    - 支持以 workflow run id 为条件检索
    - 支持以 work node id 为条件检索
    - 支持以日志等级为条件检索

    排序说明：
    - 指定 workflow_run_id 时：严格按 sequence 升序排序，确保同一workflow内日志顺序正确
    - 跨 workflow 查询时：按 timestamp + sequence 排序，保证时间顺序的合理性

    分页说明：
    - 首次查询：不传 last_sequence，获取从序列号1开始的日志
    - 后续查询：传入上次结果的 next_sequence 作为 last_sequence，从该序列号开始获取
    - last_sequence=5 表示从序列号5开始获取（包含序列号5）
    - 返回的 next_sequence 是下次查询的起始序列号

    Args:
        user_id: 用户ID
        workflow_run_id: 工作流运行ID，必填
        work_node_id: 工作节点ID，可选
        log_level: 日志等级过滤，可选
        last_sequence: 起始序列号，从该序列号开始获取日志（包含该序列号），可选
        limit: 返回数量限制，默认5条

    Returns:
        QueryWorkflowLogsResponse: 包含工作流日志列表和分页信息的响应

    Raises:
        HTTPException: 当workflow_run不存在或权限不足时
    """
    # 校验 workflow_run_id 并检查权限
    workflow_run_collection = mongodb.get_collection("workflow_run")
    try:
        query_result = await workflow_run_collection.find_one(
            {"_id": ObjectId(workflow_run_id)}
        )
    except Exception:
        # ObjectId 格式无效
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid workflow run id format: {workflow_run_id}",
        )

    if not query_result:
        logger.error(f"No workflow run found, id:{workflow_run_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow run not found",
        )

    workflow_run = WorkflowRunModel(**query_result)

    # 校验 workflow 的 owner 是否和 user_id 一致 (防止攻击者查看他人的日志)
    if workflow_run.owner not in [user_id, "*"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this workflow run logs",
        )

    # 创建工作流日志仓库实例
    log_repository = WorkflowLogRepository(mongodb.db)

    # 基于序列号的分页查询
    logs = await log_repository.get_workflow_logs_by_filters(
        user_id=user_id,
        workflow_run_id=workflow_run_id,
        work_node_id=work_node_id,
        log_level=log_level,
        last_sequence=last_sequence,
        limit=limit + 1,  # 多查询一条来判断是否还有更多
    )

    # 判断是否还有更多日志
    has_more = len(logs) > limit
    if has_more:
        logs = logs[:limit]  # 只返回指定数量

    # 获取下一页的起始序列号
    next_sequence = None
    if logs and has_more:
        last_log = logs[-1]  # 当前批次最后一条日志
        next_sequence = last_log.get("sequence")
        if next_sequence is not None:
            next_sequence += 1  # 下次从这个序列号开始（避免重复）

    # 构造响应数据
    response_data = QueryWorkflowLogsResponseData(
        logs=[WorkflowLog(**log) for log in logs],
        has_more=has_more,
        next_sequence=next_sequence,
    )

    return QueryWorkflowLogsResponse(data=response_data)
