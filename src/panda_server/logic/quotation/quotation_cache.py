"""
行情数据缓存
避免重复查询数据库
"""
import logging
import time
from typing import List, Optional, Dict
from threading import Lock

logger = logging.getLogger(__name__)


class QuotationCache:
    """行情数据缓存类"""
    
    def __init__(self, cache_timeout: int = 300):
        """
        初始化缓存
        
        Args:
            cache_timeout: 缓存超时时间（秒），默认5分钟
        """
        self._cache: Dict[str, Dict] = {}
        self._lock = Lock()
        self._cache_timeout = cache_timeout
        
    def _get_cache_key(
        self,
        quotation: str,
        quotation_type: str,
        period: str,
        start_date: Optional[str],
        end_date: Optional[str]
    ) -> str:
        """生成缓存键"""
        return f"{quotation}_{quotation_type}_{period}_{start_date}_{end_date}"
    
    def get(
        self,
        quotation: str,
        quotation_type: str,
        period: str,
        start_date: Optional[str],
        end_date: Optional[str]
    ) -> Optional[List[dict]]:
        """
        获取缓存数据
        
        Returns:
            如果缓存存在且未过期，返回数据；否则返回None
        """
        key = self._get_cache_key(quotation, quotation_type, period, start_date, end_date)
        
        with self._lock:
            if key in self._cache:
                cache_item = self._cache[key]
                # 检查是否过期
                if time.time() - cache_item['timestamp'] < self._cache_timeout:
                    logger.info(f"缓存命中: {key}, 数据量: {len(cache_item['data'])}")
                    return cache_item['data']
                else:
                    # 缓存过期，删除
                    del self._cache[key]
                    logger.info(f"缓存过期: {key}")
        
        return None
    
    def set(
        self,
        quotation: str,
        quotation_type: str,
        period: str,
        start_date: Optional[str],
        end_date: Optional[str],
        data: List[dict]
    ) -> None:
        """
        设置缓存数据
        """
        key = self._get_cache_key(quotation, quotation_type, period, start_date, end_date)
        
        with self._lock:
            self._cache[key] = {
                'data': data,
                'timestamp': time.time()
            }
            logger.info(f"缓存数据: {key}, 数据量: {len(data)}")
    
    def clear(self) -> None:
        """清空所有缓存"""
        with self._lock:
            self._cache.clear()
            logger.info("缓存已清空")
    
    def clean_expired(self) -> int:
        """
        清理过期缓存
        
        Returns:
            清理的缓存数量
        """
        current_time = time.time()
        expired_keys = []
        
        with self._lock:
            for key, item in self._cache.items():
                if current_time - item['timestamp'] >= self._cache_timeout:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self._cache[key]
        
        if expired_keys:
            logger.info(f"清理了 {len(expired_keys)} 个过期缓存")
        
        return len(expired_keys)
    
    def get_stats(self) -> dict:
        """获取缓存统计信息"""
        with self._lock:
            return {
                'size': len(self._cache),
                'keys': list(self._cache.keys()),
                'timeout': self._cache_timeout
            }


# 创建全局单例
quotation_cache = QuotationCache(cache_timeout=300)  # 5分钟缓存

