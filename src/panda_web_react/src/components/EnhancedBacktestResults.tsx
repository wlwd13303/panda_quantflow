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
} from 'antd';
import {
  LineChartOutlined,
  TransactionOutlined,
  FileTextOutlined,
  BarChartOutlined,
  FundOutlined,
  ReloadOutlined,
  SettingOutlined,
} from '@ant-design/icons';
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
  onLoadResults: () => void;
  onManualComplete: () => void;
  onConfigChange?: (config: BacktestConfig) => void;
  onStrategyNameChange?: (name: string) => void;
  onAutoRefreshChange?: (enabled: boolean) => void;
  onRefreshIntervalChange?: (interval: number) => void;
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
  { key: 'logs', icon: <FileTextOutlined />, label: '日志输出' },
  { key: 'analysis', icon: <BarChartOutlined />, label: '绩效分析' },
  { key: 'settings', icon: <SettingOutlined />, label: '策略代码' },
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
  onLoadResults,
  onManualComplete,
  onConfigChange,
  onStrategyNameChange,
  onAutoRefreshChange,
  onRefreshIntervalChange,
}) => {
  const [selectedMenu, setSelectedMenu] = useState('overview');

  // 交易表格列定义
  const tradeColumns = [
    {
      title: '日期',
      dataIndex: 'date',
      key: 'date',
      width: 100,
      render: (date: string) => String(date).substring(0, 8).replace(/(\d{4})(\d{2})(\d{2})/, '$1-$2-$3'),
    },
    { title: '股票代码', dataIndex: 'code', key: 'code', width: 110 },
    {
      title: '方向',
      dataIndex: 'direction',
      key: 'direction',
      width: 70,
      render: (direction: string) => (
        <Tag color={direction === 'buy' ? 'green' : 'red'}>
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

  // 持仓表格列定义（与监控 API 数据字段匹配）
  const positionColumns = [
    {
      title: '股票代码',
      dataIndex: 'symbol',
      key: 'symbol',
      width: 120,
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
          <span style={{ color: val >= 0 ? '#3f8600' : '#cf1322', fontWeight: 500 }}>
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
          <span style={{ color: val >= 0 ? '#3f8600' : '#cf1322' }}>
            {val >= 0 ? '+' : ''}{val.toFixed(2)}%
          </span>
        );
      },
    },
  ];

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
              <EnhancedProfitChart profitData={profitData} config={config} />
            </div>

          </div>
        );

      case 'trades':
        return (
          <Card style={{ margin: 20 }} title="交易详情">
            {tradeData.length > 0 ? (
              <Table
                columns={tradeColumns}
                dataSource={tradeData}
                pagination={{
                  pageSize: 20,
                  showTotal: (total) => `共 ${total} 条交易记录`,
                  showSizeChanger: true,
                  showQuickJumper: true,
                }}
                size="small"
                scroll={{ y: 500 }}
                rowKey={(record, index) => index?.toString() || '0'}
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
                columns={positionColumns}
                dataSource={positionData}
                pagination={{
                  pageSize: 20,
                  showTotal: (total) => `共 ${total} 条持仓记录`,
                  showSizeChanger: true,
                  showQuickJumper: true,
                }}
                size="small"
                scroll={{ y: 500 }}
                rowKey={(record, index) => index?.toString() || '0'}
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

      case 'analysis':
        return (
          <div>
            <PerformanceMetrics profitData={profitData} config={config} />
            <Card style={{ margin: 20 }} title="详细分析">
              <Text type="secondary">更多分析图表开发中...</Text>
            </Card>
          </div>
        );

      case 'settings':
        return (
          <Card style={{ margin: 20 }} title="回测参数配置">
            <Form layout="vertical" size="small">
              <Form.Item label="策略名称">
                <Input
                  value={strategyName}
                  onChange={(e) => onStrategyNameChange?.(e.target.value)}
                  placeholder="请输入策略名称"
                />
              </Form.Item>

              <Form.Item label="初始资金(万)">
                <InputNumber
                  style={{ width: '100%' }}
                  min={1}
                  max={100000}
                  value={config.start_capital}
                  onChange={(value) => onConfigChange?.({ ...config, start_capital: value || 1000 })}
                />
              </Form.Item>

              <Form.Item label="佣金费率(‰)">
                <InputNumber
                  style={{ width: '100%' }}
                  min={0}
                  max={10}
                  step={0.1}
                  precision={2}
                  value={config.commission_rate}
                  onChange={(value) => onConfigChange?.({ ...config, commission_rate: value || 1 })}
                />
              </Form.Item>

              <Form.Item label="开始日期">
                <Input
                  value={config.start_date}
                  onChange={(e) => onConfigChange?.({ ...config, start_date: e.target.value })}
                  placeholder="YYYYMMDD"
                />
              </Form.Item>

              <Form.Item label="结束日期">
                <Input
                  value={config.end_date}
                  onChange={(e) => onConfigChange?.({ ...config, end_date: e.target.value })}
                  placeholder="YYYYMMDD"
                />
              </Form.Item>

              <Form.Item label="数据频率">
                <Select
                  value={config.frequency}
                  onChange={(value) => onConfigChange?.({ ...config, frequency: value })}
                >
                  <Select.Option value="1d">日线</Select.Option>
                  <Select.Option value="1m">分钟线</Select.Option>
                </Select>
              </Form.Item>

              <Form.Item label="基准指数">
                <Select
                  value={config.standard_symbol}
                  onChange={(value) => onConfigChange?.({ ...config, standard_symbol: value })}
                >
                  <Select.Option value="000001.SH">上证指数</Select.Option>
                  <Select.Option value="000300.SH">沪深300</Select.Option>
                  <Select.Option value="000905.SH">中证500</Select.Option>
                </Select>
              </Form.Item>
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

