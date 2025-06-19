from common.logging.system_log import logging, setup_logging
import mimetypes
import sys
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from panda_server.config.database import mongodb
from panda_server.config.env import *
from panda_plugins.utils.work_node_loader import load_all_nodes
from panda_server.queue.workflow_runner import WorkflowRunner
from panda_server.utils.rabbitmq_utils import AsyncRabbitMQ
from panda_server.routes import (
    base_routes,
    plugins_routes,
    workflow_routes,
    backtest_route,
)
from starlette.staticfiles import StaticFiles
from pathlib import Path
import os
# Add project root path to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))  

# Load .env file if exsits
import dotenv
dotenv.load_dotenv()

logger = logging.getLogger(__name__)

# 获取当前文件所在目录的父目录的父目录（即项目根目录）
BASE_DIR = Path(__file__).resolve().parent.parent.parent
print("base_dir:" + str(BASE_DIR))

# 将项目根目录下的 src 目录加入模块搜索路径
sys.path.append(str(BASE_DIR / "src"))

# Define lifespan for FastAPI
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management"""

    # MongoDB connection logic
    logger.info("Connecting to MongoDB...")
    await mongodb.connect_db()
    logger.info("MongoDB connection successful")
    
    # Initialize local database indexes
    await mongodb.init_local_db()

    logger.info("Loading work nodes...")
    load_all_nodes()
    logger.info("Work nodes loading completed")

    # RabbitMQ connection logic
    if RUN_MODE == "CLOUD":
        # Test RabbitMQ connection
        rabbitmq_client = AsyncRabbitMQ()
        logger.info(f"Connecting to RabbitMQ...")
        await rabbitmq_client.test_connect()
        logger.info("RabbitMQ connection successful")

        # strat workers
        workflow_runner = WorkflowRunner()
        workflow_runner.start(rabbitmq_client)

    # Application runtime
    yield

    # Shutdown logic
    logger.info("Closing MongoDB connection...")
    await mongodb.close_db()
    logger.info("MongoDB connection closed")
    if RUN_MODE == "CLOUD":
        logger.info("Closing RabbitMQ connection...")
        await rabbitmq_client.close()
        logger.info("RabbitMQ connection closed")


app = FastAPI(
    title="PandaAI QuantFlow API",
    description="PandaAI QuantFlow API",
    version="1.0.0",
    lifespan=lifespan,
)

# 获取当前文件所在目录
current_dir = Path(__file__).resolve().parent
# 获取上一级目录
parent_dir = current_dir.parent
# 获取上一级目录中的另一个文件夹
frontend_folder = parent_dir / "panda_web"
logger.info(f"前端静态资源文件夹路径:{frontend_folder}")
# 显式设置 .js .css 的 MIME 类型
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("application/javascript", ".js")
app.mount("/quantflow", StaticFiles(directory=frontend_folder, html=True), name="quantflow")
app.mount("/charts", StaticFiles(directory=frontend_folder, html=True), name="charts")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Should set specific domains in production environment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(base_routes.router)
app.include_router(plugins_routes.router)
app.include_router(workflow_routes.router)
app.include_router(backtest_route.router)


if __name__ == "__main__":
    # Deliberately repeated once to prevent other project modules from overriding logging configuration
    setup_logging()
    # Start Uvicorn server
    uvicorn.run(
        "main:app",
        reload=True,
        host="0.0.0.0",
        port=8000,
        log_config=None,  # Disable Uvicorn default log configuration
    )
