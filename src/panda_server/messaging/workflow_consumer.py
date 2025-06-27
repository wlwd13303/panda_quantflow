import asyncio
import logging
from panda_server.config.env import (
    WORKFLOW_EXCHANGE_NAME,
    WORKFLOW_ROUTING_KEY,
    WORKFLOW_RUN_QUEUE,
)
from panda_server.messaging.rabbitmq_client import AsyncRabbitMQ
from panda_server.utils.run_workflow_utils import mark_workflow_run_failed, run_workflow_in_background

logger = logging.getLogger(__name__)


async def process_workflow_message(content):
    """处理workflow运行消息"""
    await run_workflow_in_background(content)


class WorkflowConsumer:
    """工作流执行消费者"""
    
    def __init__(self):
        pass

    async def single_worker(self, worker_id: int, client: AsyncRabbitMQ):
        """单个工作流执行worker"""
        try:
            logger.info(
                f"⚡ workflow execution worker {worker_id} started listening to queue: {WORKFLOW_RUN_QUEUE}"
            )
            await client.consume(
                queue_name=WORKFLOW_RUN_QUEUE,
                exchange_name=WORKFLOW_EXCHANGE_NAME,
                routing_key=WORKFLOW_ROUTING_KEY,
                callback=process_workflow_message,
            )
        except Exception as e:
            logger.error(f"workflow execution worker {worker_id} failed: {str(e)}")
            await mark_workflow_run_failed(
                workflow_run_id=0, error_message=f"workflow execution worker {worker_id} error: {str(e)}"
            )

    async def start_workers(self, client: AsyncRabbitMQ, worker_count: int):
        """启动多个工作流执行worker"""
        logger.info(f"🚀 Creating {worker_count} workflow execution workers")
        for i in range(worker_count):
            asyncio.create_task(self.single_worker(i, client)) 