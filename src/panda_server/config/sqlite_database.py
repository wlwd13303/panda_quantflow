"""SQLite 数据库连接和管理模块
用于存储本地策略、回测等业务数据
"""
import logging
import aiosqlite
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class SQLiteDatabase:
    """SQLite 数据库连接管理类"""
    
    db_path: Optional[Path] = None
    _connection_pool = {}
    
    @classmethod
    def set_db_path(cls, db_path: str):
        """设置数据库文件路径"""
        cls.db_path = Path(db_path)
        # 确保数据库目录存在
        cls.db_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"SQLite database path set to: {cls.db_path}")
    
    @classmethod
    @asynccontextmanager
    async def get_connection(cls):
        """获取数据库连接（异步上下文管理器）"""
        if cls.db_path is None:
            raise Exception("Database path not set. Call set_db_path() first.")
        
        conn = await aiosqlite.connect(
            str(cls.db_path),
            timeout=30.0  # 增加超时时间到30秒，避免 database is locked 错误
        )
        # 启用 WAL 模式，允许并发读写
        await conn.execute("PRAGMA journal_mode=WAL")
        # 启用外键约束
        await conn.execute("PRAGMA foreign_keys = ON")
        # 设置繁忙超时（毫秒）
        await conn.execute("PRAGMA busy_timeout = 30000")
        # 设置行工厂，以字典形式返回结果
        conn.row_factory = aiosqlite.Row
        try:
            yield conn
        finally:
            await conn.close()
    
    @classmethod
    async def init_database(cls):
        """初始化数据库表结构"""
        logger.info("Initializing SQLite database schema...")
        
        async with cls.get_connection() as conn:
            # ========== 策略表 ==========
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS panda_strategy (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    code TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    user_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 创建策略表唯一索引（确保策略名称不重复）
            await conn.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_strategy_name_unique 
                ON panda_strategy(name)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_strategy_updated_at 
                ON panda_strategy(updated_at DESC)
            """)
            
            # ========== 回测主表 ==========
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS panda_back_test (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT UNIQUE NOT NULL,
                    strategy_name TEXT NOT NULL,
                    strategy_id TEXT,
                    strategy_code TEXT,
                    start_date TEXT,
                    end_date TEXT,
                    start_capital REAL,
                    commission_rate REAL,
                    frequency TEXT,
                    standard_symbol TEXT,
                    matching_type INTEGER,
                    account_id TEXT,
                    account_type INTEGER,
                    slippage REAL,
                    margin_rate REAL,
                    start_future_capital REAL,
                    start_fund_capital REAL,
                    status TEXT DEFAULT 'pending',
                    progress REAL DEFAULT 0.0,
                    error_message TEXT,
                    result TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP
                )
            """)
            
            # 创建回测表索引
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_backtest_run_id 
                ON panda_back_test(run_id)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_backtest_status 
                ON panda_back_test(status)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_backtest_created_at 
                ON panda_back_test(created_at DESC)
            """)
            
            # ========== 回测账户数据表 ==========
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS panda_backtest_account (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    back_id TEXT NOT NULL,
                    date TEXT,
                    available REAL,
                    balance REAL,
                    cash REAL,
                    market_value REAL,
                    total_value REAL,
                    position_profit REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (back_id) REFERENCES panda_back_test(run_id) ON DELETE CASCADE
                )
            """)
            
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_account_back_id 
                ON panda_backtest_account(back_id)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_account_date 
                ON panda_backtest_account(date)
            """)
            
            # ========== 回测持仓数据表 ==========
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS panda_backtest_position (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    back_id TEXT NOT NULL,
                    date TEXT,
                    symbol TEXT,
                    contract_name TEXT,
                    volume REAL,
                    available REAL,
                    avg_price REAL,
                    market_price REAL,
                    market_value REAL,
                    profit REAL,
                    profit_rate REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (back_id) REFERENCES panda_back_test(run_id) ON DELETE CASCADE
                )
            """)
            
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_position_back_id 
                ON panda_backtest_position(back_id)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_position_date 
                ON panda_backtest_position(date)
            """)
            
            # ========== 回测收益数据表 ==========
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS panda_backtest_profit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    back_id TEXT NOT NULL,
                    date TEXT,
                    total_value REAL,
                    profit REAL,
                    profit_rate REAL,
                    cumulative_profit REAL,
                    cumulative_profit_rate REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (back_id) REFERENCES panda_back_test(run_id) ON DELETE CASCADE
                )
            """)
            
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_profit_back_id 
                ON panda_backtest_profit(back_id)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_profit_date 
                ON panda_backtest_profit(date)
            """)
            
            # ========== 回测交易数据表 ==========
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS panda_backtest_trade (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    back_id TEXT NOT NULL,
                    date TEXT,
                    time TEXT,
                    symbol TEXT,
                    contract_name TEXT,
                    direction TEXT,
                    offset TEXT,
                    price REAL,
                    volume REAL,
                    amount REAL,
                    commission REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (back_id) REFERENCES panda_back_test(run_id) ON DELETE CASCADE
                )
            """)
            
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_trade_back_id 
                ON panda_backtest_trade(back_id)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_trade_date 
                ON panda_backtest_trade(date)
            """)
            
            # ========== 回测策略日志表 ==========
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS panda_user_strategy_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    relation_id TEXT NOT NULL,
                    back_id TEXT,
                    log_level TEXT,
                    message TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    sort INTEGER,
                    FOREIGN KEY (back_id) REFERENCES panda_back_test(run_id) ON DELETE CASCADE
                )
            """)
            
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_log_relation_id 
                ON panda_user_strategy_log(relation_id)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_log_sort 
                ON panda_user_strategy_log(sort)
            """)
            
            await conn.commit()
            logger.info("SQLite database schema initialization completed")
    
    @classmethod
    async def migrate_database(cls):
        """数据库迁移：为现有表添加新列"""
        async with cls.get_connection() as conn:
            # 检查 panda_backtest_position 表是否有 contract_name 列
            cursor = await conn.execute("PRAGMA table_info(panda_backtest_position)")
            columns = await cursor.fetchall()
            column_names = [col[1] for col in columns]
            
            if 'contract_name' not in column_names:
                logger.info("Migrating: Adding contract_name column to panda_backtest_position")
                await conn.execute("ALTER TABLE panda_backtest_position ADD COLUMN contract_name TEXT")
                await conn.commit()
                logger.info("Migration completed: contract_name column added to panda_backtest_position")
            
            # 检查 panda_backtest_trade 表是否有 contract_name 列
            cursor = await conn.execute("PRAGMA table_info(panda_backtest_trade)")
            columns = await cursor.fetchall()
            column_names = [col[1] for col in columns]
            
            if 'contract_name' not in column_names:
                logger.info("Migrating: Adding contract_name column to panda_backtest_trade")
                await conn.execute("ALTER TABLE panda_backtest_trade ADD COLUMN contract_name TEXT")
                await conn.commit()
                logger.info("Migration completed: contract_name column added to panda_backtest_trade")
    
    @classmethod
    async def close_db(cls):
        """关闭数据库连接"""
        logger.info("SQLite database connections closed")


# 创建全局实例
sqlite_db = SQLiteDatabase()


