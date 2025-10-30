// 策略相关类型
export interface Strategy {
  id: string;
  _id?: string;
  name: string;
  code: string;
  description?: string;
  created_at?: string;
  updated_at?: string;
  // 🆕 工作台新增字段
  default_backtest_config?: BacktestConfig;  // 默认回测配置
  backtest_count?: number;  // 回测次数统计
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
  // 🆕 工作台新增字段
  strategy_id?: string;  // 关联的策略ID
  strategy_code_snapshot?: string;  // 回测时的策略代码快照
  config?: BacktestConfig;  // 完整的回测配置
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
  symbol?: string;          // 监控 API 字段
  contract_code?: string;
  code?: string;
  position?: number;
  volume?: number;
  avg_price?: number;
  cost_price?: number;
  now_price?: number;
  current_price?: number;
  profit?: number;
  profit_rate?: number;     // 监控 API 字段（收益率）
  market_value?: number;    // 监控 API 字段（市值）
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

// 监控数据 - 最新账户状态
export interface MonitorAccountData {
  date?: string;
  total_asset?: number;
  available?: number;
  market_value?: number;
  profit?: number;
  profit_rate?: number;
}

// 监控数据 - 最近交易
export interface MonitorTradeData {
  date?: string;
  time?: string;
  symbol?: string;
  side?: number;
  direction?: string;
  price?: number;
  volume?: number;
  amount?: number;
}

// 监控数据 - 最新持仓
export interface MonitorPositionData {
  date?: string;
  symbol?: string;
  volume?: number;
  market_value?: number;
  profit?: number;
  profit_rate?: number;
}

// 监控数据 - 净值曲线点
export interface EquityCurvePoint {
  date?: string;
  value?: number;
}

// 监控数据 - 完整响应
export interface BacktestMonitorData {
  success: boolean;
  back_id: string;
  status?: string;
  progress?: number;
  stats?: {
    account_count: number;
    trade_count: number;
    position_count: number;
    profit_count: number;
  };
  latest_account?: MonitorAccountData;
  recent_trades?: MonitorTradeData[];
  latest_positions?: MonitorPositionData[];
  equity_curve?: EquityCurvePoint[];
  error?: string;
}

// 🆕 工作台Tab类型
export type WorkspaceTabType = 'strategy' | 'backtest' | 'management';

// 🆕 工作台Tab数据
export interface WorkspaceTab {
  id: string;  // 唯一标识
  type: WorkspaceTabType;
  title: string;
  closable: boolean;  // 是否可关闭
  
  // 策略Tab特有数据
  strategyData?: {
    strategyId: string;  // 策略ID，'new'表示新建策略
    strategyName: string;
    code: string;
    description?: string;
    unsavedChanges: boolean;  // 是否有未保存的修改
    defaultConfig?: BacktestConfig;  // 默认回测配置
  };
  
  // 回测Tab特有数据
  backtestData?: {
    backtestId: string;
    backtestName: string;
    status: 'pending' | 'running' | 'completed' | 'failed';
    progress?: number;
    strategyId?: string;  // 关联的策略ID
    strategyName?: string;
    strategyCodeSnapshot?: string;  // 代码快照
    config?: BacktestConfig;
  };
}

