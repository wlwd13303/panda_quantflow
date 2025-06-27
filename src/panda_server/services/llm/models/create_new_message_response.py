from pydantic import BaseModel
from panda_server.models.base_api_response import BaseAPIResponse
from .message_model import MessageCreateModel

class CreateNewMessageResponseData(BaseModel):
    """创建新消息响应数据"""
    message: MessageCreateModel

class CreateNewMessageResponse(BaseAPIResponse[CreateNewMessageResponseData]):
    """创建新消息响应"""
    pass 