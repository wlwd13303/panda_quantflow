import logging
from panda_server.config.env import PANDA_SERVER_WORKFLOW_WORKERS
from panda_server.messaging.rabbitmq_client import AsyncRabbitMQ
from panda_server.messaging.workflow_consumer import WorkflowConsumer
from panda_server.messaging.log_consumer import LogConsumer

logger = logging.getLogger(__name__)


class QueueConsumerManager:
    """队列消费者管理器（统一管理所有类型的消费者）"""
    
    def __init__(self):
        self.workflow_consumer = WorkflowConsumer()
        self.log_consumer = LogConsumer()

    async def start_all_consumers(self, client: AsyncRabbitMQ):
        """启动所有消费者"""
        
        # 启动工作流执行消费者
        workflow_workers = PANDA_SERVER_WORKFLOW_WORKERS
        logger.info(f"🚀 Starting {workflow_workers} workflow execution consumers")
        await self.workflow_consumer.start_workers(client, workflow_workers)
        
        # 启动工作流日志消费者（使用较少的worker）
        log_workers = max(1, PANDA_SERVER_WORKFLOW_WORKERS // 2)
        logger.info(f"🚀 Starting {log_workers} workflow log consumers")
        await self.log_consumer.start_workers(client, log_workers)
        
        logger.info(f"✅ All consumers started successfully - Total workers: {workflow_workers + log_workers}")


# 为了保持向后兼容，保留原来的 WorkflowRunner 类
class WorkflowRunner(QueueConsumerManager):
    """向后兼容的工作流运行器（已重构为消费者管理器）"""
    
    def __init__(self):
        super().__init__()
        logger.warning("WorkflowRunner is deprecated, please use QueueConsumerManager instead")

    async def start(self, client: AsyncRabbitMQ):
        """启动消费者（向后兼容方法）"""
        await self.start_all_consumers(client) 