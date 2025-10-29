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
} from '@/types';

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
    name: string;
    code: string;
    description?: string;
  }): Promise<Strategy> {
    const response = await apiClient.post<ApiResponse<Strategy>>('/api/strategy/', data);
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
    return response.data.data || { back_test_id: response.data.back_test_id || '' };
  },

  // 查询回测进度
  async getProgress(backId: string): Promise<BacktestProgress> {
    const response = await apiClient.get<ApiResponse<BacktestProgress>>(
      '/api/backtest/progress',
      {
        params: { back_id: backId },
      }
    );
    return response.data.data || response.data;
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
    const response = await apiClient.get('/api/backtest/delete', {
      params: { back_id: backId },
    });
    return response.data;
  },
};

export default {
  strategy: strategyApi,
  backtest: backtestApi,
};

