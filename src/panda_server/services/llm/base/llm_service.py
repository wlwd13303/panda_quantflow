from typing import List
from panda_server.config.env import LLM_API_KEY, LLM_MODEL, LLM_BASE_URL
from panda_server.services.llm.models.message_model import Message
import openai
import traceback
import logging

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self, system_prompt: str):
        self.system_prompt = system_prompt

        self.client = openai.OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)

        # 定义系统提示词
        self.system_message = {"role": "system", "content": self.system_prompt}

    def _prepare_messages(self, messages: List[Message]):
        """转换消息格式以适配 OpenAI API 格式 (json)"""
        formatted_messages = []

        # 添加历史消息
        for msg in [m for m in messages if m.role != "system"]:
            formatted_messages.append({"role": msg.role, "content": msg.content})

        # 添加(或覆盖)系统提示词
        formatted_messages.insert(0, self.system_message)
        
        return formatted_messages

    async def chat_completion(self, messages: List[Message], json_mode: bool = False) -> str:
        """发送聊天请求到 LLM API"""
        try:
            # 格式化消息
            formatted_messages = self._prepare_messages(messages)

            response = self.client.chat.completions.create(
                model=LLM_MODEL,
                messages=formatted_messages,
                temperature=0,
                stream=False,
                response_format={"type": "json_object"} if json_mode else None,
            )
            content = response.choices[0].message.content
            return content if content is not None else ""
        except Exception as e:
            traceback.print_exc()
            logger.error(f"调用 LLM API 失败: {str(e)}")
            raise

    async def chat_completion_stream(self, messages, json_mode: bool = False):
        """发送流式聊天请求到 LLM API"""
        try:
            # 格式化消息
            formatted_messages = self._prepare_messages(messages)

            stream = self.client.chat.completions.create(
                model=LLM_MODEL,
                messages=formatted_messages,
                temperature=0,
                response_format={"type": "json_object"} if json_mode else None,
                stream=True,
            )

            for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    yield content
        except Exception as e:
            traceback.print_exc()
            logger.error(f"调用 LLM API 流式请求失败: {str(e)}")
            raise
