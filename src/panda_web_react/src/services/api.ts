import axios, { AxiosInstance } from 'axios';
import type {
  Strategy,
  BacktestRecord,
  BacktestProgress,
  AccountData,
  ProfitData,
  PositionData,
  TradeData,
  ApiResponse,
  PaginatedData,
  BacktestMonitorData,
  LogQueryResponse,
} from '@/types';
import { quotationCache } from '@/utils/quotationCache';

const API_BASE = 'http://localhost:8000';

// 创建 axios 实例
const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器
apiClient.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    console.error('API Error:', error);
    return Promise.reject(error);
  }
);

// ============ 策略相关 API ============

export const strategyApi = {
  // 获取策略列表
  async getStrategies(page = 1, pageSize = 100): Promise<Strategy[]> {
    const response = await apiClient.get<ApiResponse<Strategy[]>>('/api/strategy/', {
      params: { page, page_size: pageSize },
    });
    return response.data.data || [];
  },

  // 获取单个策略
  async getStrategy(id: string): Promise<Strategy> {
    const response = await apiClient.get<ApiResponse<Strategy>>(`/api/strategy/${id}`);
    return response.data.data!;
  },

  // 保存策略
  async saveStrategy(data: {
    id?: string;
    name: string;
    code: string;
    description?: string;
    default_backtest_config?: any;
  }): Promise<Strategy> {
    // 如果有 id，则更新现有策略；否则创建新策略
    if (data.id) {
      // 从 data 中移除 id 字段，因为 updateStrategy 的第一个参数已经是 id 了
      const { id, ...updateData } = data;
      return await this.updateStrategy(id, updateData);
    } else {
      const response = await apiClient.post<ApiResponse<Strategy>>('/api/strategy/', data);
      return response.data.data!;
    }
  },

  // 更新策略
  async updateStrategy(id: string, data: Partial<Strategy>): Promise<Strategy> {
    const response = await apiClient.put<ApiResponse<Strategy>>(`/api/strategy/${id}`, data);
    return response.data.data!;
  },

  // 删除策略
  async deleteStrategy(id: string): Promise<void> {
    await apiClient.delete(`/api/strategy/${id}`);
  },
};

// ============ 回测相关 API ============

export const backtestApi = {
  // 启动回测
  async startBacktest(data: {
    strategy_code: string;
    strategy_name: string;
    strategy_id?: string;
    start_date: string;
    end_date: string;
    start_capital: number;
    commission_rate: number;
    frequency: string;
    standard_symbol: string;
    matching_type: number;
    account_id: string;
    account_type: number;
    slippage: number;
    margin_rate: number;
    start_future_capital: number;
    start_fund_capital: number;
  }): Promise<{ back_test_id: string }> {
    const response = await apiClient.post<ApiResponse<{ back_test_id: string }>>(
      '/api/backtest/start',
      data
    );
    return response.data.data || { back_test_id: (response.data as any).back_test_id || '' };
  },

  // 查询回测进度
  async getProgress(backId: string): Promise<BacktestProgress> {
    const response = await apiClient.get<ApiResponse<BacktestProgress>>(
      '/api/backtest/progress',
      {
        params: { back_id: backId },
      }
    );
    return (response.data.data || response.data) as BacktestProgress;
  },

  // 获取账户数据
  async getAccountData(
    backId: string,
    page = 1,
    pageSize = 1000
  ): Promise<PaginatedData<AccountData>> {
    const response = await apiClient.get<ApiResponse<PaginatedData<AccountData>>>(
      '/api/backtest/account',
      {
        params: { back_id: backId, page, page_size: pageSize },
      }
    );
    const data = response.data.data || { items: [], total: 0 };
    return {
      items: Array.isArray(data) ? data : data.items || [],
      total: Array.isArray(data) ? data.length : data.total || 0,
    };
  },

  // 获取收益数据
  async getProfitData(
    backId: string,
    page = 1,
    pageSize = 1000
  ): Promise<PaginatedData<ProfitData>> {
    const response = await apiClient.get<ApiResponse<PaginatedData<ProfitData>>>(
      '/api/backtest/profit',
      {
        params: { back_id: backId, page, page_size: pageSize },
      }
    );
    const data = response.data.data || { items: [], total: 0 };
    return {
      items: Array.isArray(data) ? data : data.items || [],
      total: Array.isArray(data) ? data.length : data.total || 0,
    };
  },

  // 获取持仓数据
  async getPositionData(
    backId: string,
    page = 1,
    pageSize = 100
  ): Promise<PaginatedData<PositionData>> {
    const response = await apiClient.get<ApiResponse<PaginatedData<PositionData>>>(
      '/api/backtest/position',
      {
        params: { back_id: backId, page, page_size: pageSize },
      }
    );
    const data = response.data.data || { items: [], total: 0 };
    return {
      items: Array.isArray(data) ? data : data.items || [],
      total: Array.isArray(data) ? data.length : data.total || 0,
    };
  },

  // 获取交易数据
  async getTradeData(
    backId: string,
    page = 1,
    pageSize = 50
  ): Promise<PaginatedData<TradeData>> {
    const response = await apiClient.get<ApiResponse<PaginatedData<TradeData>>>(
      '/api/backtest/trade',
      {
        params: { back_id: backId, page, page_size: pageSize },
      }
    );
    const data = response.data.data || { items: [], total: 0 };
    return {
      items: Array.isArray(data) ? data : data.items || [],
      total: Array.isArray(data) ? data.length : data.total || 0,
    };
  },

  // 获取回测列表
  async getBacktestList(
    page = 1,
    pageSize = 20,
    status?: string
  ): Promise<PaginatedData<BacktestRecord>> {
    const params: any = { page, page_size: pageSize };
    if (status) params.status = status;

    const response = await apiClient.get<ApiResponse<PaginatedData<BacktestRecord>>>(
      '/api/backtest/list',
      { params }
    );
    return response.data.data || { items: [], total: 0 };
  },

  // 删除回测
  async deleteBacktest(backId: string): Promise<any> {
    const response = await apiClient.delete('/api/backtest/delete', {
      params: { back_id: backId },
    });
    return response.data;
  },

  // 获取回测监控数据
  async getMonitorData(backId: string): Promise<BacktestMonitorData> {
    const response = await apiClient.get<BacktestMonitorData>(
      '/api/backtest/monitor',
      {
        params: { back_id: backId },
      }
    );
    return response.data;
  },

  // 获取回测详细信息（包含配置）
  async getBacktestDetail(backId: string): Promise<BacktestRecord> {
    const response = await apiClient.get<ApiResponse<BacktestRecord>>(
      '/api/backtest/backtest',
      {
        params: { back_id: backId },
      }
    );
    return (response.data.data || response.data) as BacktestRecord;
  },

  // 获取回测日志
  async getLogs(
    relationId: string,
    lastSort?: number,
    limit: number = 100
  ): Promise<LogQueryResponse> {
    const params: any = { relation_id: relationId, limit };
    if (lastSort !== undefined) {
      params.last_sort = lastSort;
    }
    const response = await apiClient.get<ApiResponse<LogQueryResponse>>(
      '/api/backtest/userstrategylog',
      { params }
    );
    return response.data.data || { items: [], cursor: { limit } };
  },
};

// ============ 行情数据相关 API ============

export const quotationApi = {
  // 获取指数行情数据（带缓存）
  async getIndexData(
    symbol: string,
    startDate: string,
    endDate: string
  ): Promise<any[]> {
    try {
      // 先检查缓存
      const cachedData = quotationCache.get(symbol, startDate, endDate);
      if (cachedData) {
        return cachedData;
      }

      // 缓存未命中，从服务器获取数据
      console.log(`[QuotationAPI] 从服务器获取数据: ${symbol}, ${startDate}-${endDate}`);
      const response = await apiClient.get('/instrument/queryLiveData', {
        params: {
          quotation: symbol,
          quotationType: 'index',
          period: '1d',
          startDate: startDate,
          endDate: endDate,
          limit: 5000,
        },
      });

      const data = response.data.data || [];
      
      // 将数据存入缓存
      if (data.length > 0) {
        quotationCache.set(symbol, startDate, endDate, data);
      }

      return data;
    } catch (error) {
      console.error('获取指数数据失败:', error);
      return [];
    }
  },

  // 获取股票K线数据
  async getStockKLineData(
    symbol: string,
    startDate: string,
    endDate: string
  ): Promise<any[]> {
    try {
      // 转换股票代码格式（如果还没有后缀，添加.SH或.SZ）
      const formattedSymbol = this.formatStockSymbol(symbol);
      
      console.log(`[QuotationAPI] 获取股票K线数据: ${symbol} -> ${formattedSymbol}, ${startDate}-${endDate}`);
      const response = await apiClient.get('/instrument/queryLiveData', {
        params: {
          quotation: formattedSymbol,
          quotationType: 'stock',
          period: '1d',
          startDate: startDate,
          endDate: endDate,
          limit: 5000,
        },
      });

      const data = response.data.data || [];
      return data;
    } catch (error) {
      console.error('获取股票K线数据失败:', error);
      return [];
    }
  },

  // 格式化股票代码，添加交易所后缀
  formatStockSymbol(code: string): string {
    // 如果已经有后缀，直接返回
    if (code.includes('.')) {
      return code;
    }
    
    // 根据股票代码判断交易所
    // 600xxx, 601xxx, 603xxx, 605xxx, 688xxx, 689xxx 是上海
    // 000xxx, 001xxx, 002xxx, 003xxx, 300xxx 是深圳
    const codeNum = parseInt(code);
    if (isNaN(codeNum)) {
      return code; // 无法解析，返回原值
    }
    
    if (code.startsWith('6') || code.startsWith('9')) {
      return `${code}.SH`;
    } else {
      return `${code}.SZ`;
    }
  },

  // 清空行情缓存
  clearCache(): void {
    quotationCache.clear();
  },

  // 获取缓存统计信息
  getCacheStats() {
    return quotationCache.getStats();
  },
};

export default {
  strategy: strategyApi,
  backtest: backtestApi,
  quotation: quotationApi,
};

