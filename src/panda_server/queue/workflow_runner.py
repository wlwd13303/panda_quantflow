import asyncio
from panda_server.config.env import (
    PANDA_SERVER_WORKFLOW_WORKERS,
    WORKFLOW_EXCHANGE_NAME,
    WORKFLOW_ROUTING_KEY,
    WORKFLOW_RUN_QUEUE,
)
from panda_server.utils.rabbitmq_utils import AsyncRabbitMQ
from panda_server.utils.run_workflow_utils import mark_workflow_run_failed, run_workflow_in_background

import logging

logger = logging.getLogger(__name__)


class WorkflowRunner:
    def __init__(self):
        pass

    async def single_worker(self, worker_id: int, client: AsyncRabbitMQ):
        """Single workflow runner worker execution logic"""
        try:
            logger.info(
                f"workflow runner worker {worker_id} started listening to queue: {WORKFLOW_RUN_QUEUE}"
            )
            await client.consume(
                queue_name=WORKFLOW_RUN_QUEUE,
                exchange_name=WORKFLOW_EXCHANGE_NAME,
                routing_key=WORKFLOW_ROUTING_KEY,
                callback=run_workflow_in_background,
            )
        except Exception as e:
            logger.error(f"workflow runner worker {worker_id} execution failed: {str(e)}")
            await mark_workflow_run_failed(
                workflow_run_id=0, error_message=f"workflow runner worker {worker_id} error: {str(e)}"
            )

    def start(self, client: AsyncRabbitMQ):
        logger.info(
            f"Creating {PANDA_SERVER_WORKFLOW_WORKERS} workflow runner workers as background tasks"
        )
        for i in range(PANDA_SERVER_WORKFLOW_WORKERS):
            asyncio.create_task(self.single_worker(i, client))
