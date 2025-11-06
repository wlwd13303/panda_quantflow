import React, { useState } from 'react';
import {
  Layout,
  Menu,
  Card,
  Table,
  Tag,
  Button,
  Space,
  Empty,
  Statistic,
  Row,
  Col,
  Typography,
  Form,
  InputNumber,
  Input,
  Select,
  Alert,
  Modal,
} from 'antd';
import {
  LineChartOutlined,
  TransactionOutlined,
  FileTextOutlined,
  BarChartOutlined,
  FundOutlined,
  ReloadOutlined,
  SettingOutlined,
  CodeOutlined,
  EditOutlined,
  CopyOutlined,
  ExclamationCircleOutlined,
  StockOutlined,
} from '@ant-design/icons';
import Editor from '@monaco-editor/react';
import type {
  ProfitData,
  TradeData,
  PositionData,
  AccountData,
  DataStats,
  BacktestConfig,
} from '@/types';
import PerformanceMetrics from './PerformanceMetrics';
import EnhancedProfitChart from './EnhancedProfitChart';
import TradeAnalysis from './TradeAnalysis';

const { Sider, Content } = Layout;
const { Title, Text } = Typography;

interface EnhancedBacktestResultsProps {
  backtesting: boolean;
  currentBacktestId?: string;
  backtestProgress: number;
  backtestStatus: 'pending' | 'running' | 'completed' | 'failed';
  profitData: ProfitData[];
  tradeData: TradeData[];
  positionData: PositionData[];
  accountData: AccountData[];
  dataStats: DataStats;
  config: BacktestConfig;
  strategyName: string;
  autoRefresh?: boolean;
  refreshInterval?: number;
  // 🆕 策略相关属性
  strategyId?: string;
  strategyCodeSnapshot?: string;
  currentStrategyCode?: string;
  onLoadResults: () => void;
  onManualComplete: () => void;
  onConfigChange?: (config: BacktestConfig) => void;
  onStrategyNameChange?: (name: string) => void;
  onAutoRefreshChange?: (enabled: boolean) => void;
  onRefreshIntervalChange?: (interval: number) => void;
  // 🆕 策略操作回调
  onEditStrategy?: (strategyId: string) => void;
  onRerunBacktest?: (config: BacktestConfig) => void;
}

type MenuItem = {
  key: string;
  icon: React.ReactNode;
  label: string;
};

const menuItems: MenuItem[] = [
  { key: 'overview', icon: <LineChartOutlined />, label: '收益概述' },
  { key: 'trades', icon: <TransactionOutlined />, label: '交易详情' },
  { key: 'positions', icon: <FundOutlined />, label: '持仓信息' },
  { key: 'trade_analysis', icon: <StockOutlined />, label: '交易分析' },
  { key: 'analysis', icon: <BarChartOutlined />, label: '绩效分析' },
  { key: 'logs', icon: <FileTextOutlined />, label: '日志输出' },
  { key: 'strategy_code', icon: <CodeOutlined />, label: '策略代码' },
  { key: 'settings', icon: <SettingOutlined />, label: '回测配置' },
];

const EnhancedBacktestResults: React.FC<EnhancedBacktestResultsProps> = ({
  backtesting,
  currentBacktestId,
  backtestProgress,
  backtestStatus,
  profitData,
  tradeData,
  positionData,
  accountData,
  dataStats,
  config,
  strategyName,
  autoRefresh = true,
  refreshInterval = 2000,
  strategyId,
  strategyCodeSnapshot,
  currentStrategyCode,
  onLoadResults,
  onManualComplete,
  onConfigChange,
  onStrategyNameChange,
  onAutoRefreshChange,
  onRefreshIntervalChange,
  onEditStrategy,
  onRerunBacktest,
}) => {
  const [selectedMenu, setSelectedMenu] = useState('overview');

  // 检查策略代码是否已变更
  const strategyCodeChanged = strategyCodeSnapshot && currentStrategyCode && strategyCodeSnapshot !== currentStrategyCode;

  // 生成交易表格列配置（包含日期和股票筛选）
  const getTradeColumns = () => {
    // 提取所有唯一日期并排序
    const uniqueDates = Array.from(new Set(tradeData.map(t => t.date).filter(Boolean)))
      .sort((a, b) => (b || '').localeCompare(a || ''));
    
    const dateFilters = uniqueDates.map(date => ({
      text: String(date).substring(0, 8).replace(/(\d{4})(\d{2})(\d{2})/, '$1-$2-$3'),
      value: date || '',
    }));
    
    // 提取所有唯一股票代码并排序
    const uniqueSymbols = Array.from(new Set(tradeData.map(t => t.code).filter(Boolean)))
      .sort();
    
    const symbolFilters = uniqueSymbols.map(symbol => ({
      text: symbol || 'N/A',
      value: symbol || '',
    }));
    
    return [
      {
        title: '日期',
        dataIndex: 'date',
        key: 'date',
        width: 110,
        align: 'center' as const,
        filters: dateFilters,
        filterSearch: true,
        onFilter: (value: any, record: TradeData) => record.date === value,
        render: (date: string) => String(date).substring(0, 8).replace(/(\d{4})(\d{2})(\d{2})/, '$1-$2-$3'),
      },
      {
        title: '股票代码',
        dataIndex: 'code',
        key: 'code',
        width: 110,
        align: 'center' as const,
        filters: symbolFilters,
        filterSearch: true,
        onFilter: (value: any, record: TradeData) => record.code === value,
      },
      {
        title: '方向',
        dataIndex: 'direction',
        key: 'direction',
        width: 80,
        align: 'center' as const,
        filters: [
          { text: '买入', value: 'buy' },
          { text: '卖出', value: 'sell' },
        ],
        onFilter: (value: any, record: TradeData) => record.direction === value,
        render: (direction: string) => (
          <Tag color={direction === 'buy' ? 'red' : 'green'}>
            {direction === 'buy' ? '买入' : '卖出'}
          </Tag>
        ),
      },
      {
        title: '数量',
        dataIndex: 'amount',
        key: 'amount',
        width: 90,
        align: 'right' as const,
        render: (amount: number) => amount.toLocaleString(),
      },
      {
        title: '价格',
        dataIndex: 'price',
        key: 'price',
        width: 90,
        align: 'right' as const,
        render: (price: string) => `¥${price}`,
      },
      {
        title: '金额',
        dataIndex: 'cost',
        key: 'cost',
        width: 120,
        align: 'right' as const,
        render: (cost: string) => `¥${parseFloat(cost).toLocaleString()}`,
      },
    ];
  };

  // 生成持仓列配置（包含日期和股票筛选）
  const getPositionColumns = () => {
    // 提取所有唯一日期并排序
    const uniqueDates = Array.from(new Set(positionData.map(p => p.date || p.gmt_create).filter(Boolean)))
      .sort((a, b) => (b || '').localeCompare(a || ''));
    
    const dateFilters = uniqueDates.map(date => ({
      text: (() => {
        if (!date) return 'N/A';
        if (date.length === 8) {
          return `${date.substring(0, 4)}-${date.substring(4, 6)}-${date.substring(6, 8)}`;
        }
        return date;
      })(),
      value: date || '',
    }));
    
    // 提取所有唯一股票代码并排序
    const uniqueSymbols = Array.from(new Set(positionData.map(p => p.symbol || p.contract_code || p.code).filter(Boolean)))
      .sort();
    
    const symbolFilters = uniqueSymbols.map(symbol => ({
      text: symbol || 'N/A',
      value: symbol || '',
    }));
    
    return [
      {
        title: '日期',
        dataIndex: 'date',
        key: 'date',
        width: 110,
        fixed: 'left' as const,
        align: 'center' as const,
        filters: dateFilters,
        filterSearch: true,
        onFilter: (value: any, record: PositionData) => {
          const recordDate = record.date || record.gmt_create || '';
          return recordDate === value;
        },
        render: (date: string, record: PositionData) => {
          const dateValue = date || record.gmt_create;
          if (!dateValue) return 'N/A';
          if (dateValue.length === 8) {
            return `${dateValue.substring(0, 4)}-${dateValue.substring(4, 6)}-${dateValue.substring(6, 8)}`;
          }
          return dateValue;
        },
      },
      {
        title: '股票代码',
        dataIndex: 'symbol',
        key: 'symbol',
        width: 120,
        align: 'center' as const,
        filters: symbolFilters,
        filterSearch: true,
        onFilter: (value: any, record: PositionData) => {
          const recordSymbol = record.symbol || record.contract_code || record.code || '';
          return recordSymbol === value;
        },
        render: (symbol: string, record: PositionData) => 
          symbol || record.contract_code || record.code || 'N/A',
      },
      {
        title: '持仓量',
        dataIndex: 'volume',
        key: 'volume',
        width: 100,
        align: 'right' as const,
        render: (volume: number) => (volume || 0).toLocaleString(),
      },
      {
        title: '市值',
        dataIndex: 'market_value',
        key: 'market_value',
        width: 120,
        align: 'right' as const,
        render: (market_value: number) => {
          const val = market_value || 0;
          return `¥${val.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
        },
      },
      {
        title: '盈亏',
        dataIndex: 'profit',
        key: 'profit',
        width: 120,
        align: 'right' as const,
        render: (profit: number) => {
          const val = profit || 0;
          return (
            <span style={{ color: val >= 0 ? '#cf1322' : '#3f8600', fontWeight: 500 }}>
              {val >= 0 ? '+' : ''}¥{val.toFixed(2)}
            </span>
          );
        },
      },
      {
        title: '收益率',
        dataIndex: 'profit_rate',
        key: 'profit_rate',
        width: 100,
        align: 'right' as const,
        render: (profit_rate: number) => {
          const val = (profit_rate || 0) * 100;
          return (
            <span style={{ color: val >= 0 ? '#cf1322' : '#3f8600' }}>
              {val >= 0 ? '+' : ''}{val.toFixed(2)}%
            </span>
          );
        },
      },
    ];
  };

  const latestAccount = accountData.length > 0 ? accountData[accountData.length - 1] : null;

  // 渲染不同的内容区域
  const renderContent = () => {
    switch (selectedMenu) {
      case 'overview':
        return (
          <div>

            {/* 性能指标 */}
            <PerformanceMetrics profitData={profitData} config={config} />

            {/* 净值曲线 */}
            <div style={{ padding: '0 20px 20px 20px' }}>
              <EnhancedProfitChart 
                profitData={profitData} 
                config={{
                  start_capital: config.start_capital,
                  start_date: config.start_date,
                  end_date: config.end_date,
                  standard_symbol: config.standard_symbol
                }} 
              />
            </div>

          </div>
        );

      case 'trades':
        return (
          <Card style={{ margin: 20 }} title="交易详情">
            {tradeData.length > 0 ? (
              <Table
                columns={getTradeColumns()}
                dataSource={tradeData}
                pagination={{
                  pageSize: 20,
                  showTotal: (total) => `共 ${total} 条交易记录`,
                  showSizeChanger: true,
                  showQuickJumper: true,
                }}
                size="small"
                scroll={{ x: 800, y: 500 }}
                rowKey={(record, index) => `${record.date}_${record.code}_${index}` || index?.toString() || '0'}
              />
            ) : (
              <Empty description="暂无交易数据" />
            )}
          </Card>
        );

      case 'positions':
        return (
          <Card style={{ margin: 20 }} title="持仓信息">
            {positionData.length > 0 ? (
              <Table
                columns={getPositionColumns()}
                dataSource={positionData}
                pagination={{
                  pageSize: 20,
                  showTotal: (total) => `共 ${total} 条持仓记录`,
                  showSizeChanger: true,
                  showQuickJumper: true,
                }}
                size="small"
                scroll={{ x: 800, y: 500 }}
                rowKey={(record, index) => `${record.date}_${record.symbol}_${index}` || index?.toString() || '0'}
              />
            ) : (
              <Empty description="暂无持仓数据" />
            )}
          </Card>
        );

      case 'logs':
        return (
          <Card style={{ margin: 20 }} title="日志输出">
            <div style={{ 
              background: '#f5f5f5', 
              padding: 16, 
              borderRadius: 4,
              fontFamily: 'monospace',
              fontSize: 12,
              maxHeight: 600,
              overflow: 'auto'
            }}>
              <Text type="secondary">回测日志功能开发中...</Text>
              <br />
              <Text type="secondary">策略名称: {strategyName}</Text>
              <br />
              <Text type="secondary">回测ID: {currentBacktestId}</Text>
              <br />
              <Text type="secondary">开始日期: {config.start_date}</Text>
              <br />
              <Text type="secondary">结束日期: {config.end_date}</Text>
              <br />
              <Text type="secondary">初始资金: ¥{(config.start_capital * 10000).toLocaleString()}</Text>
            </div>
          </Card>
        );

      case 'trade_analysis':
        return (
          <TradeAnalysis
            tradeData={tradeData}
            positionData={positionData}
            backtestId={currentBacktestId}
          />
        );

      case 'analysis':
        return (
          <div>
            <PerformanceMetrics profitData={profitData} config={config} />
            <div style={{ padding: '0 20px 20px 20px' }}>
              <EnhancedProfitChart 
                profitData={profitData} 
                config={{
                  start_capital: config.start_capital,
                  start_date: config.start_date,
                  end_date: config.end_date,
                  standard_symbol: config.standard_symbol
                }} 
              />
            </div>
            <Card style={{ margin: 20 }} title="详细分析">
              <Text type="secondary">更多分析图表开发中...</Text>
            </Card>
          </div>
        );

      case 'strategy_code':
        return (
          <Card style={{ margin: 20 }} title="策略代码快照">
            <Space direction="vertical" style={{ width: '100%', marginBottom: 16 }}>
              <Alert
                message="代码快照说明"
                description="这是启动回测时的策略代码快照，用于复现和审计回测结果。"
                type="info"
                showIcon
              />
              
              {strategyCodeChanged && (
                <Alert
                  message="⚠️ 策略代码已被修改"
                  description={
                    <div>
                      <div style={{ marginBottom: 8 }}>
                        当前策略库中的代码与回测时的代码不一致，编辑的将是最新版本。
                      </div>
                      <Button
                        size="small"
                        type="link"
                        onClick={() => {
                          Modal.info({
                            title: '代码对比',
                            width: 800,
                            content: (
                              <div>
                                <p>回测时的代码快照与当前策略代码不同。</p>
                                <p style={{ color: '#999', fontSize: 12 }}>
                                  详细对比功能开发中，未来将支持逐行对比显示。
                                </p>
                              </div>
                            ),
                          });
                        }}
                      >
                        查看差异对比
                      </Button>
                    </div>
                  }
                  type="warning"
                  showIcon
                />
              )}
              
              <Space>
                {strategyId && onEditStrategy && (
                  <Button
                    icon={<EditOutlined />}
                    onClick={() => {
                      if (strategyCodeChanged) {
                        Modal.confirm({
                          title: '策略代码已变更',
                          icon: <ExclamationCircleOutlined />,
                          content: (
                            <div>
                              <p>当前策略库中的代码与回测时的代码不一致。</p>
                              <p>编辑的将是策略库中的<strong>最新版本</strong>，而非此回测使用的版本。</p>
                            </div>
                          ),
                          okText: '继续编辑最新版本',
                          cancelText: '取消',
                          onOk: () => {
                            onEditStrategy(strategyId);
                          },
                        });
                      } else {
                        onEditStrategy(strategyId);
                      }
                    }}
                  >
                    编辑此策略
                  </Button>
                )}
                
                <Button
                  icon={<CopyOutlined />}
                  onClick={() => {
                    if (strategyCodeSnapshot) {
                      navigator.clipboard.writeText(strategyCodeSnapshot);
                      Modal.success({
                        title: '复制成功',
                        content: '策略代码已复制到剪贴板',
                      });
                    }
                  }}
                >
                  复制代码
                </Button>
                
                {onRerunBacktest && (
                  <Button
                    icon={<ReloadOutlined />}
                    onClick={() => {
                      Modal.confirm({
                        title: '重新运行回测',
                        content: '确定要使用相同配置重新运行回测吗？',
                        okText: '确定',
                        cancelText: '取消',
                        onOk: () => {
                          onRerunBacktest(config);
                        },
                      });
                    }}
                  >
                    使用相同配置重新运行
                  </Button>
                )}
              </Space>
            </Space>
            
            {/* 只读代码编辑器 */}
            <div style={{ border: '1px solid #d9d9d9', borderRadius: 4 }}>
              <Editor
                height="600px"
                language="python"
                value={strategyCodeSnapshot || '// 暂无代码快照'}
                options={{
                  readOnly: true,
                  minimap: { enabled: true },
                  scrollBeyondLastLine: false,
                  wordWrap: 'on',
                  fontSize: 14,
                }}
                theme="vs-dark"
              />
            </div>
          </Card>
        );

      case 'settings':
        return (
          <Card style={{ margin: 20 }} title="回测配置信息">
            <Form layout="vertical" size="small">
              <Form.Item label="策略名称">
                <Input
                  value={strategyName}
                  disabled
                />
              </Form.Item>

              <Form.Item label="初始资金(万)">
                <InputNumber
                  style={{ width: '100%' }}
                  value={config.start_capital}
                  disabled
                />
              </Form.Item>

              <Form.Item label="佣金费率(‰)">
                <InputNumber
                  style={{ width: '100%' }}
                  value={config.commission_rate}
                  disabled
                />
              </Form.Item>

              <Form.Item label="开始日期">
                <Input
                  value={config.start_date}
                  disabled
                />
              </Form.Item>

              <Form.Item label="结束日期">
                <Input
                  value={config.end_date}
                  disabled
                />
              </Form.Item>

              <Form.Item label="数据频率">
                <Select
                  value={config.frequency}
                  disabled
                >
                  <Select.Option value="1d">日线</Select.Option>
                  <Select.Option value="1m">分钟线</Select.Option>
                </Select>
              </Form.Item>

              <Form.Item label="基准指数">
                <Select
                  value={config.standard_symbol}
                  disabled
                >
                  <Select.Option value="000001.SH">上证指数</Select.Option>
                  <Select.Option value="000300.SH">沪深300</Select.Option>
                  <Select.Option value="000905.SH">中证500</Select.Option>
                </Select>
              </Form.Item>
              
              <Alert
                message="配置为只读"
                description="回测配置在回测启动后不可修改。如需修改，请重新运行回测。"
                type="info"
                showIcon
              />
            </Form>
          </Card>
        );

      default:
        return null;
    }
  };

  return (
    <Layout style={{ height: 'calc(100vh - 140px)', background: '#fff' }}>
      <Sider
        width={180}
        style={{
          background: '#fff',
          borderRight: '1px solid #e8e8e8',
        }}
      >
        <Menu
          mode="inline"
          selectedKeys={[selectedMenu]}
          onClick={({ key }) => setSelectedMenu(key)}
          style={{ height: '100%', borderRight: 0 }}
          items={menuItems}
        />
      </Sider>
      <Layout style={{ background: '#f5f5f5' }}>
        <Content style={{ overflow: 'auto' }}>
          {renderContent()}
        </Content>
      </Layout>
    </Layout>
  );
};

export default EnhancedBacktestResults;

