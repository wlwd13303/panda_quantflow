import logging
from fastapi import APIRouter, Body, Header, Query, status, HTTPException
from typing import Optional, List
from enum import Enum
import traceback
from panda_server.models.general_code_assistant_response import GeneralCodeAssistantResponse
from panda_server.services.llm.models.get_session_list_response import GetSessionListResponse
from panda_server.services.llm.enums.assistant_type import AssistantType
from panda_server.services.llm.logic.get_session_list_logic import get_session_list_logic
from panda_server.services.llm.logic.create_new_message_logic import create_new_message_logic
from panda_server.services.llm.models.create_new_message_request import CreateNewMessageRequest
from panda_server.services.llm.models.create_new_message_response import CreateNewMessageResponse
from panda_server.services.llm.logic.get_session_detail_logic import get_session_detail_logic
from panda_server.services.llm.models.get_session_detail_response import GetSessionDetailResponse
from panda_server.services.llm.logic.delete_session_logic import delete_session_logic
from panda_server.services.llm.models.delete_session_response import DeleteSessionResponse


# 获取 logger
logger = logging.getLogger(__name__)

# 创建路由实例，设置前缀和标签
router = APIRouter(prefix="/api/chat", tags=["chat"])

# # TODO: @cgt
# @router.post("/code-assistant")
# async def chat_backtest_assistant(
#     uid: str = Header(..., alias="uid", description="用户ID"),
#     session_id: str|None = Body(None, description="会话ID"),
#     message: str = Body(..., description="用户消息"),
#     original_code: str|None = Body(None, description="需要AI参考的当前版本代码"),
#     last_run_log: str|None = Body(None, description="上次运行日志, 用于给 AI 提供debug信息"),
# ) -> CodeAssistantResponse:
#     pass

# TODO: @cgt
@router.post("/backtest-assistant")
async def chat_backtest_assistant(
    uid: str = Header(..., alias="uid", description="用户ID"),
    session_id: str|None = Body(None, description="会话ID"),
    message: str = Body(..., description="用户消息"),
    original_code: str|None = Body(None, description="需要AI参考的当前版本代码"),
    last_run_log: str|None = Body(None, description="上次运行日志, 用于给 AI 提供debug信息"),
) -> GeneralCodeAssistantResponse:
    """处理聊天请求"""
    # try:
    #     # 使用流式处理
    #     async def generate():
    #         try:
    #             # async for chunk in chat_service.process_message_stream(
    #             async for chunk in chat_service.process_message_stream(
    #                 request.user_id,
    #                 request.message,
    #                 request.session_id
    #             ):
    #                 yield f"data: {json.dumps({'content': chunk})}\n\n"
    #         except ValueError as e:
    #             yield f"data: {json.dumps({'error': str(e)})}\n\n"
    #         except Exception as e:
    #             yield f"data: {json.dumps({'error': '处理消息时发生错误'})}\n\n"
    #         finally:
    #             yield "data: [DONE]\n\n"

    #     return StreamingResponse(
    #         generate(),
    #         media_type="text/event-stream"
    #     )
    # except Exception as e:
    #     raise HTTPException(status_code=500, detail=str(e))



@router.post("/session/new-message", response_model=CreateNewMessageResponse, status_code=status.HTTP_200_OK)
async def create_new_message(
    uid: str = Header(..., alias="uid", description="用户ID"),
    request_data: CreateNewMessageRequest = Body(..., description="消息请求数据")
) -> CreateNewMessageResponse:
    """
    创建新消息
    
    支持两种场景：
    1. 如果不提供session_id，则创建新的会话
    2. 如果提供session_id，则向现有会话添加消息
    
    Args:
        uid: 从 headers 中获取的用户ID
        request_data: 消息请求数据，包含role、content和可选的session_id
        
    Returns:
        CreateNewMessageResponse: 包装后的响应对象
    """
    try:
        return await create_new_message_logic(uid, request_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"请求参数错误: {str(e)}",
        )
    except Exception as e:
        stack_trace = traceback.format_exc()
        logger.error(f"创建消息时发生意外错误: {e}\n{stack_trace}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建消息时发生意外错误",
        )


@router.get(
    "/session/all", response_model=GetSessionListResponse, status_code=status.HTTP_200_OK
)
async def get_session_list(
    uid: str = Header(..., alias="uid", description="用户ID"),
    page: int = Query(1, description="第几页，从1开始", ge=1),
    limit: int = Query(10, description="每页返回的数量", ge=1, le=100),
) -> GetSessionListResponse:
    """
    获取用户的聊天会话列表（支持分页）

    Args:
        uid: 从 headers 中获取的用户ID
        page: 第几页，从1开始，默认1
        limit: 每页返回的数量，默认10，最大100

    Returns:
        GetSessionListResponse: 包含聊天会话列表和总数的响应
    """
    try:
        return await get_session_list_logic(uid, limit, page)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"请求参数错误: {str(e)}",
        )
    except Exception as e:
        stack_trace = traceback.format_exc()
        logger.error(f"获取聊天会话列表时发生意外错误: {e}\n{stack_trace}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取聊天会话列表时发生意外错误",
        )


@router.get(
    "/session/detail", response_model=GetSessionDetailResponse, status_code=status.HTTP_200_OK
)
async def get_session_detail(
    session_id: str = Query(..., description="会话ID"),
    uid: str = Header(..., alias="uid", description="用户ID"),
) -> GetSessionDetailResponse:
    """
    获取指定会话的详细信息

    Args:
        session_id: 会话ID（查询参数）
        uid: 从 headers 中获取的用户ID

    Returns:
        GetSessionDetailResponse: 包含会话详情的响应
    """
    try:
        return await get_session_detail_logic(uid, session_id)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"请求参数错误: {str(e)}",
        )
    except Exception as e:
        stack_trace = traceback.format_exc()
        logger.error(f"获取会话详情时发生意外错误: {e}\n{stack_trace}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取会话详情时发生意外错误",
        )


@router.delete(
    "/session/delete", response_model=DeleteSessionResponse, status_code=status.HTTP_200_OK
)
async def delete_session(
    session_id: str = Query(..., description="会话ID"),
    uid: str = Header(..., alias="uid", description="用户ID"),
) -> DeleteSessionResponse:
    """
    删除指定会话（物理删除）

    Args:
        session_id: 会话ID（查询参数）
        uid: 从 headers 中获取的用户ID

    Returns:
        DeleteSessionResponse: 包含删除结果的响应
    """
    try:
        return await delete_session_logic(uid, session_id)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"请求参数错误: {str(e)}",
        )
    except Exception as e:
        stack_trace = traceback.format_exc()
        logger.error(f"删除会话时发生意外错误: {e}\n{stack_trace}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除会话时发生意外错误",
        ) 