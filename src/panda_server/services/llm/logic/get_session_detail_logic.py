import logging
from bson import ObjectId
from fastapi import HTTPException, status
from panda_server.config.database import mongodb
from panda_server.services.llm.models.get_session_detail_response import (
    GetSessionDetailResponse,
    GetSessionDetailResponseData,
)
from panda_server.services.llm.models.chat_session_model import ChatSessionModel

logger = logging.getLogger(__name__)

# 定义 collection 名称
CHAT_SESSIONS_COLLECTION = "chat_sessions"


async def get_session_detail_logic(
    user_id: str, session_id: str
) -> GetSessionDetailResponse:
    """
    获取指定用户的单个聊天会话详情

    Args:
        user_id: 用户ID
        session_id: 会话ID

    Returns:
        GetSessionDetailResponse: 包含聊天会话详情的响应

    Raises:
        ValueError: 当session_id格式无效时
        HTTPException: 当会话不存在或用户无权限访问时
    """
    chat_session_collection = mongodb.get_collection(CHAT_SESSIONS_COLLECTION)

    # 验证 session_id 格式
    if not ObjectId.is_valid(session_id):
        raise ValueError(f"无效的会话ID格式: {session_id}")

    # 构建查询条件
    query = {"_id": ObjectId(session_id), "user_id": user_id}

    # 查询会话详情
    session_doc = await chat_session_collection.find_one(query)

    if not session_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"会话不存在或您无权限访问该会话: {session_id}",
        )

    # 转换 ObjectId 为字符串
    session_doc["_id"] = str(session_doc["_id"])

    # 使用模型验证数据
    session_model = ChatSessionModel(**session_doc)

    # 构造响应数据
    response_data = GetSessionDetailResponseData(session=session_model)

    return GetSessionDetailResponse(data=response_data) 