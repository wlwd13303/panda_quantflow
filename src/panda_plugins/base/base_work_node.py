from abc import ABC, abstractmethod
import logging

from pydantic import BaseModel
from typing import Type, Optional, Dict, Any
import panda_plugins.base.jsonschema_patches  # 必须保留

class BaseWorkNode(ABC):
    """
    Base Work Node
    Base class to be inherited when developing panda_plugins
    """

    # internal class attributes
    __work_node_name__: str
    __work_node_display_name__: str
    __work_node_group__: str
    __work_node_order__: int
    __work_node_type__: str

    def __init__(self):
        # 日志记录器，由工作流执行器设置
        self._user_logger = None
        self._workflow_id = None  # 存储workflow_id
        self._sys_logger = logging.getLogger(self.__class__.__name__)

    def _setup_logging_context(self, user_id: str, workflow_run_id: str, work_node_id: str, workflow_id: str = None):
        """
        设置日志上下文，由工作流执行器调用
        
        Args:
            user_id: 用户ID
            workflow_run_id: 工作流运行ID  
            work_node_id: 工作节点ID
            workflow_id: 工作流ID
        """
        try:
            from common.logging.workflow_log import WorkflowLogger
            self._user_logger = WorkflowLogger(
                user_id=user_id,
                workflow_run_id=workflow_run_id,
                work_node_id=work_node_id
            )
            self._workflow_id = workflow_id  # 存储workflow_id以备后用
        except Exception as e:
            self._sys_logger.warning(f"Failed to setup logging context: {e}")

    def log_debug(self, message: str, **kwargs):
        """
        记录调试级别日志
        
        Args:
            message: 日志消息
            **kwargs: 额外的元数据
        """
        if self._user_logger:
            self._user_logger.debug(message, workflow_id=self._workflow_id, **kwargs)
        else:
            self._sys_logger.debug(f"[USER_LOG] {message} (metadata: {kwargs})")

    def log_info(self, message: str, **kwargs):
        """
        记录信息级别日志
        
        Args:
            message: 日志消息
            **kwargs: 额外的元数据
        """
        if self._user_logger:
            self._user_logger.info(message, workflow_id=self._workflow_id, **kwargs)
        else:
            self._sys_logger.info(f"[USER_LOG] {message} (metadata: {kwargs})")

    def log_warning(self, message: str, **kwargs):
        """
        记录警告级别日志
        
        Args:
            message: 日志消息
            **kwargs: 额外的元数据
        """
        if self._user_logger:
            self._user_logger.warning(message, workflow_id=self._workflow_id, **kwargs)
        else:
            self._sys_logger.warning(f"[USER_LOG] {message} (metadata: {kwargs})")

    def log_error(self, message: str, **kwargs):
        """
        记录错误级别日志
        
        Args:
            message: 日志消息
            **kwargs: 额外的元数据
        """
        if self._user_logger:
            self._user_logger.error(message, workflow_id=self._workflow_id, **kwargs)
        else:
            self._sys_logger.error(f"[USER_LOG] {message} (metadata: {kwargs})")

    def log_critical(self, message: str, **kwargs):
        """
        记录严重错误级别日志
        
        Args:
            message: 日志消息
            **kwargs: 额外的元数据
        """
        if self._user_logger:
            self._user_logger.critical(message, workflow_id=self._workflow_id, **kwargs)
        else:
            self._sys_logger.critical(f"[USER_LOG] {message} (metadata: {kwargs})")

    @classmethod
    @abstractmethod
    def input_model(cls) -> Optional[Type[BaseModel]]:
        """
        Returns the Pydantic model class that defines the input.
        IMPORTANT: Plugin developers must implement this method.
        """
        pass

    @classmethod
    @abstractmethod
    def output_model(cls) -> Optional[Type[BaseModel]]:
        """
        Returns the Pydantic model class that defines the output.
        IMPORTANT: Plugin developers must implement this method.
        """
        pass

    @abstractmethod
    def run(self, input: BaseModel) -> Optional[BaseModel]:
        """
        Executes node logic, receives input model as parameter and returns output model.
        IMPORTANT: Plugin developers must implement this method.
        
        Example usage in plugin:
            def run(self, input: InputModel) -> OutputModel:
                self.log_info("开始处理数据", input_size=len(input.data))
                try:
                    # 处理逻辑
                    result = process_data(input.data)
                    self.log_info("数据处理完成", output_size=len(result))
                    return OutputModel(data=result)
                except Exception as e:
                    self.log_error("数据处理失败", error=str(e))
                    raise
        """
        pass
