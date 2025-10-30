import logging
import urllib.parse

from motor.motor_asyncio import AsyncIOMotorClient
from panda_server.config.env import (
    MONGO_URI,
    DATABASE_NAME,
    RUN_MODE,
    MONGO_USER,
    MONGO_PASSWORD,
    MONGO_AUTH_DB,
    MONGO_TYPE,
    MONGO_REPLICA_SET,
)
import asyncio
from panda_server.config.mongodb_index_config import init_all_indexes

logger = logging.getLogger(__name__)

class MongoDB:
    """
    MongoDB 数据库连接管理类
    提供数据库连接、关闭和集合获取的功能
    """

    client = None  # MongoDB 客户端实例
    db = None  # 数据库实例

    @classmethod
    async def connect_db(cls):
        """
        建立数据库连接（支持认证模式和本地单节点模式）
        返回：数据库实例
        """

        # 构建通用的客户端配置参数
        client_kwargs = {
            "retryWrites": True,
            "w": "majority",
            "socketTimeoutMS": 30000,
            "connectTimeoutMS": 20000,
            "serverSelectionTimeoutMS": 30000,
        }
        if MONGO_TYPE == "replica_set":
            client_kwargs["replicaSet"] = MONGO_REPLICA_SET
        if MONGO_USER and MONGO_PASSWORD and MONGO_AUTH_DB:
            client_kwargs["username"] = MONGO_USER
            client_kwargs["password"] = MONGO_PASSWORD
            client_kwargs["authSource"] = MONGO_AUTH_DB
        # 测试连接
        try:
            cls.client = AsyncIOMotorClient(MONGO_URI, **client_kwargs)
            cls.db = cls.client.get_database(DATABASE_NAME)
            await asyncio.wait_for(cls.db.command("ping"), timeout=3)
        except Exception as e:
            raise Exception(f"MongoDB Connection Error: {e}")
        return cls.db

    @classmethod
    async def init_local_db(cls):
        """Initialize database indexes and other operations"""
        logger.info(f"Current running environment: {RUN_MODE}")
        if RUN_MODE == "LOCAL":
            logger.info("Local environment, starting database index initialization...")
            try:
                await init_all_indexes(cls)
                logger.info("Database index initialization completed")
            except Exception as e:
                error_msg = str(e)
                # 如果是认证错误，提供更友好的提示
                if "authentication" in error_msg.lower() or "Unauthorized" in error_msg:
                    logger.warning("数据库索引初始化失败：MongoDB需要认证")
                    logger.warning("提示：如果这是本地MongoDB且未启用认证，请检查:")
                    logger.warning("  1. MongoDB服务是否启用了认证")
                    logger.warning("  2. 环境变量 MONGO_USER 和 MONGO_PASSWORD 是否正确设置")
                    logger.warning("  3. 如果不需要认证，请确保MongoDB配置允许无认证连接")
                    logger.warning("索引初始化失败不影响系统基本功能，但可能影响查询性能")
                else:
                    logger.error(f"Database index initialization failed: {e}")
        else:
            logger.info("Cloud environment, skipping database index initialization")
    
    @classmethod
    async def close_db(cls):
        """
        关闭数据库连接
        """
        if cls.client:
            cls.client.close()

    @classmethod
    def get_collection(cls, collection_name: str):
        """
        获取指定名称的集合
        参数：
            collection_name: 集合名称
        返回：MongoDB 集合实例
        异常：
            Exception: 数据库未连接时抛出
        """
        if cls.db is None:
            raise Exception("Database not connected. Call connect_db() first.")
        return cls.db[collection_name]


# 创建数据库连接实例
mongodb = MongoDB()
