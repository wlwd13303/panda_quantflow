import logging
from bson import ObjectId
from fastapi import HTTPException, status
from typing import List, Optional, AsyncGenerator, Tuple
from panda_server.config.database import mongodb
from panda_server.services.llm.models.chat_session_model import (
    ChatSessionModel,
    ChatSessionCreateModel,
    ChatSessionUpdateModel,
)
from panda_server.services.llm.models.message_model import Message
from panda_server.services.llm.base.llm_service import LLMService
from panda_server.services.llm.models.delete_session_response import (
    DeleteSessionResponse,
    DeleteSessionResponseData,
)
from panda_server.services.llm.models.get_session_list_response import (
    GetSessionListResponse,
    GetSessionListResponseData,
)

logger = logging.getLogger(__name__)

# 定义 collection 名称
CHAT_SESSION_COLLECTION_NAME = "chat_sessions"


class LLMServiceUtils:

    def __init__(self, system_prompt: str | None = None):
        self.system_prompt = system_prompt or "You are a helpful assistant."
        self.llm = LLMService(self.system_prompt)

    async def process_message(
        self,
        user_id: str,
        user_message: str,
        session_id: str | None = None,
        stream: bool = False,
        json_mode: bool = False,
    ) -> Tuple[str, str] | Tuple[str, AsyncGenerator[str, None]]:
        """处理用户消息并返回 AI 响应

        Args:
            user_id: 用户 ID
            user_message: 用户消息
            session_id: 会话 ID, 如果为 None, 则创建一个新的会话
            stream: 是否流式返回
            json_mode: 是否返回 JSON 模式

        Returns:
            Tuple[str, str]: 如果非流式模式, 第一个 str 是 session_id, 第二个 str 是 AI 响应
            Tuple[str, AsyncGenerator[str, None]]: 如果流式模式, 第一个 str 是 session_id, 第二个 AsyncGenerator 是异步生成器
        """
        
        # 准备会话 session
        session = await self._session_setup(user_id, user_message, session_id)

        # 非流式模式, 返回字符串
        if not stream:
            response_msg = await self.llm.chat_completion(
                session.messages, json_mode=json_mode
            )
            await self._session_teardown(session, response_msg)
            return str(session.id), response_msg

        # 流式模式，返回异步生成器
        async def stream_generator():
            response_msg = ""
            async for chunk in self.llm.chat_completion_stream(
                session.messages, json_mode=json_mode
            ):
                response_msg += chunk
                yield chunk
            await self._session_teardown(session, response_msg)

        return str(session.id), stream_generator()

    async def _session_setup(
        self,
        user_id: str,
        user_message: str,
        session_id: str | None = None,
    ) -> ChatSessionModel:
        """准备会话 session
        返回检索到的已有 session, 或者创建新的 session 返回
        """
        # 判断是否需要创建一个新的 session 对话
        if session_id:
            try:
                session = await self.get_session_detail_logic(user_id, session_id)
            except ValueError as e:
                logger.error(f"Failed to get session: {e}")
                raise
        else:
            session = ChatSessionCreateModel(
                user_id=user_id,
                messages=[],
            )
            session: ChatSessionModel = await self.create_new_message_to_new_session(session)

        # 添加并存储用户消息
        user_msg = Message(role="user", content=user_message)
        return await self.create_new_message_to_existing_session(session, user_msg, return_updated_session=True)

    async def _session_teardown(self, session: ChatSessionModel, content: str) -> None:
        """session 结束, 存储新消息响应到 session 中"""
        ai_message = Message(role="assistant", content=content)
        await self.create_new_message_to_existing_session(session, ai_message, return_updated_session=False)



    async def get_session_list_logic(
        self, user_id: str, limit: int, page: int
    ) -> GetSessionListResponse:
        """
        查询指定用户的所有 chat session (支持分页)

        Args:
            user_id: 用户ID
            limit: 每页返回的数量
            page: 第几页，从1开始

        Returns:
            GetSessionListResponse: 包含聊天会话列表和总数的响应
        """
        chat_session_collection = mongodb.get_collection(CHAT_SESSION_COLLECTION_NAME)

        # 构建查询条件
        query = {"user_id": user_id}

        # 查询总数
        total_count = await chat_session_collection.count_documents(query)

        # 计算跳过的数量
        skip = (page - 1) * limit

        # 简单查询，在应用层处理
        cursor = chat_session_collection.find(query).sort("updated_at", -1).skip(skip).limit(limit)

        # 处理查询结果并在应用层过滤用户消息
        sessions = []
        async for doc in cursor:
            # 转换 ObjectId 为字符串
            doc["_id"] = str(doc["_id"])
            
            # 在应用层过滤最后一条用户消息
            user_messages = [msg for msg in doc.get("messages", []) if msg.get("role") == "user"]
            doc["messages"] = [user_messages[-1]] if user_messages else []
            
            # 直接使用ChatSessionModel
            session = ChatSessionModel(**doc)
            sessions.append(session)

        # 构造响应数据
        response_data = GetSessionListResponseData(
            sessions=sessions, total_count=total_count
        )

        return GetSessionListResponse(data=response_data)


    async def get_session_detail_logic(
        self, user_id: str, session_id: str
    ) -> ChatSessionModel:
        """获取指定用户的聊天会话，如果不存在则抛异常"""
        # 验证 session_id 格式
        if not ObjectId.is_valid(session_id):
            raise ValueError(f"无效的会话ID格式: {session_id}")

        # 查询会话详情
        chat_session_collection = mongodb.get_collection(CHAT_SESSION_COLLECTION_NAME)
        session_doc = await chat_session_collection.find_one({
            "_id": ObjectId(session_id), 
            "user_id": user_id
        })

        if not session_doc:
            raise ValueError(f"session_id not found: {session_id}")

        # 转换 ObjectId 为字符串并返回模型
        session_doc["_id"] = str(session_doc["_id"])
        return ChatSessionModel(**session_doc) 



    async def create_new_message_to_new_session(self, chat_session: ChatSessionCreateModel) -> ChatSessionModel:
        """创建新的session（用于内部调用，输入已验证）"""
        # 直接插入到数据库（输入已在调用方验证）
        session_dict = chat_session.model_dump(by_alias=True, exclude_unset=True)
        collection = mongodb.get_collection(CHAT_SESSION_COLLECTION_NAME)
        result = await collection.insert_one(session_dict)
        
        # 构造返回的ChatSessionModel对象
        session_dict["_id"] = str(result.inserted_id)
        return ChatSessionModel(**session_dict)


    async def create_new_message_to_existing_session(
        self, 
        session: ChatSessionModel, 
        message: Message, 
        return_updated_session: bool = False
    ) -> Optional[ChatSessionModel]:
        """统一的消息添加逻辑：向session中添加消息并更新数据库
        
        Args:
            session: 目标会话
            message: 要添加的消息
            return_updated_session: 是否返回更新后的session对象
            
        Returns:
            如果 return_updated_session 为 True，返回更新后的 ChatSessionModel，否则返回 None
        """
        # 将消息添加到session的副本中（避免直接修改原对象）
        updated_messages = session.messages + [message]
        
        # 使用 ChatSessionUpdateModel 进行数据验证
        session_update_data = ChatSessionUpdateModel(messages=updated_messages)
        
        # 更新数据库
        collection = mongodb.get_collection(CHAT_SESSION_COLLECTION_NAME)
        session_object_id = ObjectId(session.id)
        
        # 使用验证后的数据进行数据库更新
        update_dict = session_update_data.model_dump(by_alias=True, exclude_unset=True)
        
        await collection.update_one(
            {"_id": session_object_id},
            {"$set": update_dict}
        )
        
        if return_updated_session:
            # 查询并返回更新后的session
            updated_doc = await collection.find_one({"_id": session_object_id})
            updated_doc["_id"] = str(updated_doc["_id"])
            return ChatSessionModel(**updated_doc)
        else:
            # 即使不返回，也要更新原session对象的messages，保持状态一致性
            session.messages = updated_messages
        
        return None


    async def delete_session_logic(
        self, user_id: str, session_id: str
    ) -> DeleteSessionResponse:
        """
        删除指定用户的单个聊天会话（物理删除）

        Args:
            user_id: 用户ID
            session_id: 会话ID

        Returns:
            DeleteSessionResponse: 包含删除结果的响应

        Raises:
            ValueError: 当session_id格式无效时
            HTTPException: 当会话不存在或用户无权限删除时
        """
        chat_session_collection = mongodb.get_collection(CHAT_SESSION_COLLECTION_NAME)

        # 验证 session_id 格式
        if not ObjectId.is_valid(session_id):
            raise ValueError(f"无效的会话ID格式: {session_id}")

        # 构建查询条件（确保用户只能删除自己的会话）
        query = {"_id": ObjectId(session_id), "user_id": user_id}

        # 先检查会话是否存在并属于该用户
        existing_session = await chat_session_collection.find_one(query)
        
        if not existing_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"会话不存在或您无权限删除该会话: {session_id}",
            )

        # 执行物理删除
        delete_result = await chat_session_collection.delete_one(query)

        # 检查删除结果
        if delete_result.deleted_count == 0:
            logger.error(f"删除会话失败，会话ID: {session_id}, 用户ID: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="删除会话失败",
            )

        logger.info(f"成功删除会话，会话ID: {session_id}, 用户ID: {user_id}")

        # 构造响应数据
        response_data = DeleteSessionResponseData(
            session_id=session_id,
            deleted=True
        )

        return DeleteSessionResponse(data=response_data) 
