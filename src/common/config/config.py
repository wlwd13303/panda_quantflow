"""
配置模块，用于加载和管理配置信息
仅从 .env 文件加载配置，不使用系统环境变量
"""

import logging
from pathlib import Path
import re

logger = logging.getLogger(__name__)

# 配置字典，直接从 .env 文件加载
_env_config = {}

def _load_env_file(env_file_path: Path) -> dict:
    """
    直接从 .env 文件解析配置，不使用系统环境变量
    
    Args:
        env_file_path: .env 文件路径
        
    Returns:
        dict: 配置字典
    """
    config = {}
    if not env_file_path.exists():
        return config
    
    try:
        with open(env_file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                
                # 跳过空行和注释
                if not line or line.startswith('#'):
                    continue
                
                # 解析 KEY=VALUE 格式
                # 支持引号包围的值和未引号的值
                match = re.match(r'^([^=]+)=(.*)$', line)
                if match:
                    key = match.group(1).strip()
                    value = match.group(2).strip()
                    
                    # 移除引号（如果有）
                    if (value.startswith('"') and value.endswith('"')) or \
                       (value.startswith("'") and value.endswith("'")):
                        value = value[1:-1]
                    
                    # 处理空值
                    if value.lower() == '' or value.lower() == 'none':
                        value = None
                    
                    config[key] = value
                else:
                    logger.warning(f".env 文件第 {line_num} 行格式不正确: {line}")
    except Exception as e:
        logger.error(f"读取 .env 文件失败: {e}")
    
    return config

def _get_env_value(key: str, default=None):
    """
    从 .env 文件读取配置值，不使用系统环境变量
    
    Args:
        key: 配置键名
        default: 默认值
        
    Returns:
        配置值
    """
    return _env_config.get(key, default)

# 加载 .env 文件
# 获取项目根目录（config.py 位于 src/common/config/，项目根目录是四级父目录）
project_root = Path(__file__).resolve().parent.parent.parent.parent
env_file = project_root / ".env"

if env_file.exists():
    _env_config = _load_env_file(env_file)
    logger.info(f"已从 {env_file} 加载 .env 文件，共 {len(_env_config)} 个配置项")
else:
    # 尝试从当前工作目录加载
    cwd_env_file = Path.cwd() / ".env"
    if cwd_env_file.exists():
        _env_config = _load_env_file(cwd_env_file)
        logger.info(f"已从 {cwd_env_file} 加载 .env 文件，共 {len(_env_config)} 个配置项")
    else:
        logger.warning(f"未找到 .env 文件，项目根目录: {project_root}, 查找路径: {env_file}")
        logger.warning("将使用默认配置值")

# 初始化配置变量
config = None


def load_config():
    """加载配置文件，仅从 .env 文件加载，不使用系统环境变量"""
    global config
    config = {}
    # MongoDB
    config["MONGO_USER"] = _get_env_value("MONGO_USER", "panda")
    config["MONGO_PASSWORD"] = _get_env_value("MONGO_PASSWORD", "panda")
    config["MONGO_URI"] = _get_env_value("MONGO_URI", "127.0.0.1:27017")
    config["MONGO_AUTH_DB"] = _get_env_value("MONGO_AUTH_DB", "admin")
    config["MONGO_DB"] = _get_env_value("MONGO_DB", "panda")
    config["MONGO_TYPE"] = _get_env_value("MONGO_TYPE", "replica_set")
    config["MONGO_REPLICA_SET"] = _get_env_value("MONGO_REPLICA_SET", "rs0")

    # 日志配置 Logging
    config["LOG_LEVEL"] = _get_env_value("LOG_LEVEL", "DEBUG")
    config["log_file"] = _get_env_value("LOG_FILE", "logs/data_cleaner.log")
    config["log_rotation"] = _get_env_value("LOG_ROTATION", "1 MB")
    config["LOG_PATH"] = _get_env_value("LOG_PATH", "logs")

    # Redis
    config["REDIS_HOST"] = _get_env_value("REDIS_HOST", "localhost")
    config["REDIS_PORT"] = int(_get_env_value("REDIS_PORT", "6379"))
    config["REDIS_DB"] = int(_get_env_value("REDIS_DB", "0"))
    config["REDIS_PASSWORD"] = _get_env_value("REDIS_PASSWORD", "123456")
    config["REDIS_MAX_CONNECTIONS"] = int(_get_env_value("REDIS_MAX_CONNECTIONS", "10"))
    config["REDIS_SOCKET_TIMEOUT"] = int(_get_env_value("REDIS_SOCKET_TIMEOUT", "5"))
    config["REDIS_CONNECT_TIMEOUT"] = int(_get_env_value("REDIS_CONNECT_TIMEOUT", "5"))

    # MySQL
    config["MYSQL_HOST"] = _get_env_value("MYSQL_HOST", "localhost")
    config["MYSQL_PORT"] = int(_get_env_value("MYSQL_PORT", "3306"))
    config["MYSQL_USER"] = _get_env_value("MYSQL_USER", "root")
    config["MYSQL_PASSWORD"] = _get_env_value("MYSQL_PASSWORD", "qweqwe")
    config["MYSQL_DATABASE"] = _get_env_value("MYSQL_DATABASE", "pandaai_test")

    return config


def get_config():
    """
    获取配置对象，如果配置未加载则先加载配置

    Returns:
        dict: 配置信息字典
    """
    global config
    if config is None:
        config = load_config()
    return config


# 初始加载配置
try:
    config = load_config()
    logger.info(f"初始化配置成功: {config}")
except Exception as e:
    logger.error(f"初始化配置失败: {str(e)}")
    # 不在初始化时抛出异常，留到实际使用时再处理
