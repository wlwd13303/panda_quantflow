/**
 * 行情数据缓存工具
 * 避免重复请求相同的指数数据
 */

interface CacheItem {
  data: any[];
  timestamp: number;
}

class QuotationCache {
  private cache: Map<string, CacheItem> = new Map();
  private cacheTimeout: number = 5 * 60 * 1000; // 5分钟缓存时间

  /**
   * 生成缓存键
   */
  private getCacheKey(symbol: string, startDate: string, endDate: string): string {
    return `${symbol}_${startDate}_${endDate}`;
  }

  /**
   * 检查缓存是否有效
   */
  private isValid(item: CacheItem): boolean {
    return Date.now() - item.timestamp < this.cacheTimeout;
  }

  /**
   * 获取缓存数据
   */
  get(symbol: string, startDate: string, endDate: string): any[] | null {
    const key = this.getCacheKey(symbol, startDate, endDate);
    const item = this.cache.get(key);

    if (item && this.isValid(item)) {
      console.log(`[QuotationCache] 命中缓存: ${key}`);
      return item.data;
    }

    if (item) {
      // 缓存已过期，删除
      this.cache.delete(key);
      console.log(`[QuotationCache] 缓存过期: ${key}`);
    }

    return null;
  }

  /**
   * 设置缓存数据
   */
  set(symbol: string, startDate: string, endDate: string, data: any[]): void {
    const key = this.getCacheKey(symbol, startDate, endDate);
    this.cache.set(key, {
      data,
      timestamp: Date.now(),
    });
    console.log(`[QuotationCache] 缓存数据: ${key}, 数据量: ${data.length}`);
  }

  /**
   * 清空缓存
   */
  clear(): void {
    this.cache.clear();
    console.log('[QuotationCache] 缓存已清空');
  }

  /**
   * 清理过期缓存
   */
  cleanExpired(): void {
    const now = Date.now();
    let cleanedCount = 0;

    for (const [key, item] of this.cache.entries()) {
      if (!this.isValid(item)) {
        this.cache.delete(key);
        cleanedCount++;
      }
    }

    if (cleanedCount > 0) {
      console.log(`[QuotationCache] 清理了 ${cleanedCount} 个过期缓存`);
    }
  }

  /**
   * 获取缓存统计信息
   */
  getStats(): { size: number; keys: string[] } {
    return {
      size: this.cache.size,
      keys: Array.from(this.cache.keys()),
    };
  }
}

// 创建单例
export const quotationCache = new QuotationCache();

// 定期清理过期缓存（每分钟一次）
setInterval(() => {
  quotationCache.cleanExpired();
}, 60 * 1000);

