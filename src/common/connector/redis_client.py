from redis import Redis, ConnectionPool
from redis.exceptions import RedisError
import logging
from common.config.config import config

logger = logging.getLogger(__name__)

class RedisClient:
    _instance = None
    _pool = None

    def __new__(cls):
        if cls._instance is None:
            cls._init_pool()
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'client'):
            self.client = Redis(connection_pool=self._pool)

    @classmethod
    def _init_pool(cls):
        try:
            conf = cls.get_config()
            cls._pool = ConnectionPool(
                host=conf['host'],
                port=conf['port'],
                db=conf['db'],
                password=conf['password'],
                decode_responses=conf['decode_responses'],
                max_connections=conf['max_connections'],
                socket_timeout=conf['socket_timeout'],
                socket_connect_timeout=conf['socket_connect_timeout']
            )
            logger.info("Redis连接池初始化成功")
        except Exception as e:
            logger.error(f"Redis连接池初始化失败: {str(e)}")
            raise

    @classmethod
    def get_config(cls):
        return {
            'host': config['REDIS_HOST'],
            'port': config['REDIS_PORT'],
            'db': config['REDIS_DB'],
            'password': config['REDIS_PASSWORD'],
            'decode_responses': True,
            'max_connections': config['REDIS_MAX_CONNECTIONS'],
            'socket_timeout': config['REDIS_SOCKET_TIMEOUT'],
            'socket_connect_timeout': config['REDIS_CONNECT_TIMEOUT']
        }

    def set(self, key, value, time=None):
        try:
            if time:
                return self.client.setex(key, time, value)
            return self.client.set(key, value)
        except RedisError as e:
            logger.error(f"Redis set 操作失败: {str(e)}")
            return None

    def get(self, key):
        try:
            return self.client.get(key)
        except RedisError as e:
            logger.error(f"Redis get 操作失败: {str(e)}")
            return None
    def delete(self, key):
        """删除指定 key"""
        try:
            return self.client.delete(key)
        except RedisError as e:
            logger.error(f"Redis delete 操作失败: {str(e)}")
            return None
    def close(self):
        if self._pool:
            try:
                self._pool.disconnect()
                logger.info("Redis连接池已关闭")
            except Exception as e:
                logger.error(f"关闭Redis连接池失败: {str(e)}")
            finally:
                self._pool = None
                self._instance = None

        # ------------------------------------------------------------------
        # Hash helpers  ——  新增的三种 Hash 方法
        # ------------------------------------------------------------------

    def setHashRedis(self, name: str, key: str, value):
        """Equivalent to ``HSET name key value``.

        :param name: top‑level Redis key that stores the hash
        :param key:  field inside the hash
        :param value: value to set for that field
        """
        try:
            return self.client.hset(name, key, value)
        except RedisError as e:
            logger.error(f"Redis hset 操作失败: {e}")
            return None

    def getHashRedis(self, name: str, key: str | None = None):
        """Fetch one field (*key*) or the whole hash (*key* is ``None``).

        If *key* is provided this calls ``HGET name key`` and returns a single
        value. Otherwise it calls ``HGETALL`` and returns a ``dict`` mapping
        field → value.
        """
        try:
            if key is not None:
                return self.client.hget(name, key)
            return self.client.hgetall(name)
        except RedisError as e:
            logger.error(f"Redis hget/hgetall 操作失败: {e}")
            return None

    def delHashRedis(self, name: str, *keys: str):
        """Delete one/many fields or the entire hash.

        * If *keys* are given, they are deleted via ``HDEL``.
        * If *keys* is empty, the full hash key (``name``) is removed with
          ``DEL``.
        """
        try:
            if keys:
                return self.client.hdel(name, *keys)
            # 删除整个 hash 键
            return self.delete(name)
        except RedisError as e:
            logger.error(f"Redis hdel/DEL 操作失败: {e}")
            return None

