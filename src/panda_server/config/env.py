from pathlib import Path
import logging
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
# 获取项目根目录（env.py 位于 src/panda_server/config/，项目根目录是四级父目录）
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

# 运行模式: LOCAL 为用户本地运行, CLOUD 为 PandAaI 官网运行
RUN_MODE = _get_env_value("RUN_MODE", "LOCAL")
SERVER_ROLE = _get_env_value("SERVER_ROLE", "ALL")  # API, CONSUMER, ALL

# 日志配置
LOG_LEVEL = _get_env_value("LOG_LEVEL", "DEBUG")
LOG_CONSOLE = _get_env_value("LOG_CONSOLE", "true")
LOG_FILE = _get_env_value("LOG_FILE", "true")
LOG_FORMAT = _get_env_value("LOG_FORMAT", "plain")  # plain, json
LOG_CONSOLE_ANSI = _get_env_value("LOG_CONSOLE_ANSI", "true")

# MongoDB 连接配置，仅从 .env 文件加载
MONGO_URI = _get_env_value("MONGO_URI", "localhost:27017")
DATABASE_NAME = _get_env_value("DATABASE_NAME", "panda")
MONGO_USER = _get_env_value("MONGO_USER", "")  # 本地 MongoDB 通常无需认证
MONGO_PASSWORD = _get_env_value("MONGO_PASSWORD", "")  # 本地 MongoDB 通常无需认证
MONGO_AUTH_DB = _get_env_value("MONGO_AUTH_DB", "admin")
MONGO_TYPE = _get_env_value("MONGO_TYPE", "single")  # 'single' 或 'replica_set' - 本地默认使用 single
MONGO_REPLICA_SET = _get_env_value("MONGO_REPLICA_SET", "rs0")


# RabbitMQ 配置
RABBITMQ_URL = _get_env_value("RABBITMQ_URL", "amqp://admin:123456@localhost:5672")
RABBITMQ_MAX_RETRIES = _get_env_value("RABBITMQ_MAX_RETRIES", "3")
RABBITMQ_RETRY_INTERVAL = _get_env_value("RABBITMQ_RETRY_INTERVAL", "5")
RABBITMQ_PREFETCH_COUNT = _get_env_value("RABBITMQ_PREFETCH_COUNT", "3")

# 工作流队列配置
WORKFLOW_EXCHANGE_NAME = _get_env_value("WORKFLOW_EXCHANGE_NAME", "workflow.run")
WORKFLOW_ROUTING_KEY = _get_env_value("WORKFLOW_ROUTING_KEY", "workflow.run")
WORKFLOW_RUN_QUEUE = _get_env_value("WORKFLOW_RUN_QUEUE", "workflow_run")
WORKFLOW_LOG_ROUTING_KEY = _get_env_value("WORKFLOW_LOG_ROUTING_KEY", "workflow.log")
WORKFLOW_LOG_QUEUE = _get_env_value("WORKFLOW_LOG_QUEUE", "workflow_log")
PANDA_SERVER_WORKFLOW_WORKERS = _get_env_value("PANDA_SERVER_WORKFLOW_WORKERS", "5")

# LLM 相关配置
DEEPSEEK_API_KEY = _get_env_value("DEEPSEEK_API_KEY", None)

# SQLite 数据库配置
# 本地数据（策略、回测等）存储路径
SQLITE_DB_PATH = _get_env_value("SQLITE_DB_PATH", "data/panda_local.db")
