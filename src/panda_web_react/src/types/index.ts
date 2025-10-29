// 策略相关类型
export interface Strategy {
  id: string;
  _id?: string;
  name: string;
  code: string;
  description?: string;
  created_at?: string;
  updated_at?: string;
}

// 回测配置
export interface BacktestConfig {
  start_capital: number;
  start_date: string;
  end_date: string;
  frequency: string;
  commission_rate: number;
  standard_symbol: string;
  matching_type: number;
}

// 回测记录
export interface BacktestRecord {
  _id: string;
  run_id?: string;
  strategy_name: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  back_profit?: number;
  back_profit_year?: number;
  sharpe?: number;
  max_drawdown?: number;
  start_date?: string;
  end_date?: string;
  created_at: string;
  updated_at?: string;
}

// 回测进度
export interface BacktestProgress {
  progress: number;
  status: 'pending' | 'running' | 'completed' | 'failed';
  error?: string;
}

// 账户数据
export interface AccountData {
  total_profit?: number;
  available_funds?: number;
  market_value?: number;
  gmt_create?: string;
  gmt_create_time?: string;
  [key: string]: any;
}

// 收益数据
export interface ProfitData {
  date?: string;
  gmt_create?: string;
  gmt_create_time?: string;
  total_value?: number;
  total_profit?: number;
  csi_stock?: number;
  strategy_profit?: number;
  day_profit?: number;
  [key: string]: any;
}

// 持仓数据
export interface PositionData {
  contract_code?: string;
  code?: string;
  position?: number;
  volume?: number;
  avg_price?: number;
  cost_price?: number;
  now_price?: number;
  current_price?: number;
  profit?: number;
  date?: string;
  gmt_create?: string;
  [key: string]: any;
}

// 交易数据
export interface TradeData {
  date: string;
  code: string;
  direction: 'buy' | 'sell';
  amount: number;
  price: string;
  cost: string;
  trade_date?: string;
  contract_code?: string;
  volume?: number;
  [key: string]: any;
}

// API 响应格式
export interface ApiResponse<T = any> {
  success?: boolean;
  code?: number;
  message?: string;
  data?: T;
}

// 分页数据
export interface PaginatedData<T> {
  items: T[];
  total: number;
  page?: number;
  page_size?: number;
}

// 数据统计
export interface DataStats {
  accountCount: number;
  tradeCount: number;
  positionCount: number;
  profitCount: number;
}

