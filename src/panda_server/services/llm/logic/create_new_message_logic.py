import logging
from typing import Optional, Dict, Any
from panda_server.config.database import mongodb
from panda_server.services.llm.models.create_new_message_request import CreateNewMessageRequest
from panda_server.services.llm.models.message_model import MessageCreateModel
from panda_server.services.llm.models.chat_session_model import ChatSessionCreateModel, ChatSessionUpdateModel
from panda_server.services.llm.models.create_new_message_response import CreateNewMessageResponse, CreateNewMessageResponseData
from bson import ObjectId
import time

# 数据库集合名称
CHAT_SESSIONS_COLLECTION = "chat_sessions"

logger = logging.getLogger(__name__)


async def create_new_message_logic(uid: str, request_data: CreateNewMessageRequest) -> CreateNewMessageResponse:
    """
    创建消息逻辑
    
    Args:
        uid: 用户ID
        request_data: 消息请求数据
        
    Returns:
        CreateNewMessageResponse: 包装后的响应对象
    """
    try:
        # 使用 MessageCreateModel 验证和创建消息
        message = MessageCreateModel(
            role=request_data.role,
            content=request_data.content
            # timestamp 由 MessageCreateModel 自动生成
        )
        
        if request_data.session_id:
            # 场景2：向现有session添加消息
            # 先验证session_id是否存在，以及是否匹配user_id
            await create_new_message_to_existing_session(uid, request_data.session_id, message)
        else:
            # 场景1：创建新session并添加消息
            # 消息通过验证后，创建新session并将消息放入message队列
            await create_new_message_to_new_session(uid, message)
        
        return CreateNewMessageResponse(data=CreateNewMessageResponseData(message=message))
            
    except Exception as e:
        logger.error(f"创建消息时发生错误: {str(e)}")
        raise


async def create_new_message_to_new_session(uid: str, message: MessageCreateModel) -> None:
    """
    创建新的session并添加消息
    
    步骤：
    1. 消息已通过MessageCreateModel验证
    2. 创建新的ChatSessionCreateModel，将消息放入messages队列
    3. 将新session插入到数据库
    """
    try:
        # 步骤2：使用ChatSessionCreateModel验证数据并自动生成ID
        chat_session = ChatSessionCreateModel(
            user_id=uid,
            messages=[message]  # 将消息直接放入session的message队列
        )
        
        # 步骤3：转换为字典并插入到数据库
        session_dict = chat_session.model_dump(by_alias=True, exclude_unset=True)
        collection = mongodb.get_collection(CHAT_SESSIONS_COLLECTION)
        result = await collection.insert_one(session_dict)
        
        if not result.inserted_id:
            raise Exception("创建新session失败：数据库插入操作未返回ID")
        
    except Exception as e:
        logger.error(f"创建新session时发生错误: {str(e)}")
        raise Exception(f"创建新会话失败: {str(e)}")


async def create_new_message_to_existing_session(uid: str, session_id: str, message: MessageCreateModel) -> None:
    """
    向现有session添加消息
    
    步骤：
    1. 验证session_id格式是否有效
    2. 查找session是否存在
    3. 验证session的user_id是否与传入的user_id匹配
    4. 将消息添加到session的messages列表末尾
    5. 更新session的updated_at时间戳
    """
    try:
        # 获取chat_sessions集合
        collection = mongodb.get_collection(CHAT_SESSIONS_COLLECTION)
        
        # 步骤1：验证session_id格式
        try:
            session_object_id = ObjectId(session_id)
        except Exception:
            raise ValueError(f"无效的session_id格式: {session_id}")
        
        # 步骤2：查找session是否存在
        session = await collection.find_one({"_id": session_object_id})
        
        if not session:
            raise ValueError(f"Session不存在: {session_id}")
        
        # 步骤3：验证session的user_id是否与传入的user_id匹配
        if session.get("user_id") != uid:
            raise ValueError(f"Session访问权限不匹配，session所属用户与当前用户不一致")
        
        # 步骤4和5：使用ChatSessionUpdateModel验证更新数据，然后直接使用验证后的数据
        # 构建更新的session数据进行验证
        updated_messages = session.get("messages", []) + [message]
        current_timestamp = int(time.time() * 1000)
        
        # 使用ChatSessionUpdateModel验证更新数据
        update_session = ChatSessionUpdateModel(
            user_id=session.get("user_id"),
            messages=updated_messages,
            created_at=session.get("created_at"),
            updated_at=current_timestamp
        )
        
        # 验证通过后，直接使用验证后的数据执行数据库更新操作
        message_dict = message.model_dump(by_alias=True, exclude_unset=True)
        update_result = await collection.update_one(
            {"_id": session_object_id},
            {
                "$push": {"messages": message_dict},
                "$set": {"updated_at": update_session.updated_at}
            }
        )
        
        if update_result.modified_count == 0:
            raise Exception("更新session失败：没有文档被修改")
        
    except ValueError:
        # 重新抛出值错误，保持原始错误信息
        raise
    except Exception as e:
        logger.error(f"向现有session添加消息时发生错误: {str(e)}")
        raise Exception(f"添加消息失败: {str(e)}") 