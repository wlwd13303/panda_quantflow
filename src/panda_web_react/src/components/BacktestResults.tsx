import React, { useRef } from 'react';
import {
  Card,
  Row,
  Col,
  Progress,
  Button,
  Table,
  Tag,
  Empty,
  Statistic,
  Space,
  Form,
  InputNumber,
  Input,
  Select,
  Tabs,
  Divider,
  Descriptions,
} from 'antd';
import {
  ReloadOutlined,
  RiseOutlined,
  FallOutlined,
  LineChartOutlined,
  FundOutlined,
  TransactionOutlined,
  BarChartOutlined,
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import type {
  ProfitData,
  TradeData,
  PositionData,
  AccountData,
  DataStats,
  BacktestConfig,
} from '@/types';

const { TabPane } = Tabs;

interface BacktestResultsProps {
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
  onConfigChange: (config: BacktestConfig) => void;
  onStrategyNameChange: (name: string) => void;
  onLoadResults: () => void;
  onManualComplete: () => void;
}

const BacktestResults: React.FC<BacktestResultsProps> = ({
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
  onConfigChange,
  onStrategyNameChange,
  onLoadResults,
  onManualComplete,
}) => {
  const chartRef = useRef<ReactECharts>(null);

  const getStatusText = (status: string) => {
    const statusMap: Record<string, string> = {
      pending: '等待中',
      running: '运行中',
      completed: '已完成',
      failed: '失败',
    };
    return statusMap[status] || status;
  };

  const getChartOption = () => {
    const dates = profitData.map((item) => {
      const date = item.date || item.gmt_create_time || item.gmt_create || '';
      return String(date).substring(0, 8);
    });

    // 计算净值曲线：净值 = 当前资产 / 初始资金
    // 初始资金从配置中获取（单位：万），需要转换为元
    const initialCapital = (config.start_capital || 1000) * 10000;
    
    const equity = profitData.map((item) => {
      const totalAsset =
        item.total_value ?? item.total_profit ?? item.csi_stock ?? item.strategy_profit ?? 0;
      const totalAssetValue = Number(totalAsset) || 0;
      // 计算净值：当前资产 / 初始资金
      const netValue = totalAssetValue / initialCapital;
      return netValue;
    });

    // 计算收益率（最新净值 - 1）
    const latestNetValue = equity.length > 0 ? equity[equity.length - 1] : 1;
    const totalReturn = ((latestNetValue - 1) * 100).toFixed(2);

    return {
      title: {
        text: '策略净值曲线',
        subtext: `累计收益率: ${totalReturn}%`,
        left: 'center',
      },
      tooltip: {
        trigger: 'axis',
        formatter: (params: any) => {
          if (!params || !params[0]) return '';
          const netValue = params[0].value ?? 1;
          const numValue = Number(netValue);
          const returnRate = ((numValue - 1) * 100).toFixed(2);
          return (
            params[0].name +
            '<br/>' +
            params[0].marker +
            '净值: ' +
            (isNaN(numValue) ? '1.0000' : numValue.toFixed(4)) +
            '<br/>' +
            '累计收益: ' +
            returnRate +
            '%'
          );
        },
      },
      xAxis: {
        type: 'category',
        data: dates,
        axisLabel: { rotate: 45 },
      },
      yAxis: {
        type: 'value',
        name: '净值',
        scale: true,  // 不从0开始，自动缩放以适应数据范围
        axisLabel: {
          formatter: '{value}'
        },
      },
      series: [
        {
          name: '净值',
          type: 'line',
          data: equity,
          smooth: true,
          lineStyle: { color: '#5470c6', width: 2 },
          areaStyle: {
            color: {
              type: 'linear',
              x: 0,
              y: 0,
              x2: 0,
              y2: 1,
              colorStops: [
                { offset: 0, color: 'rgba(84, 112, 198, 0.3)' },
                { offset: 1, color: 'rgba(84, 112, 198, 0.05)' },
              ],
            },
          },
          markLine: {
            symbol: 'none',
            data: [
              {
                yAxis: 1,
                lineStyle: { color: '#999', type: 'dashed', width: 1 },
                label: { show: true, position: 'end', formatter: '基准线 (1.0)' }
              }
            ],
            silent: true,
          },
        },
      ],
      grid: { left: '10%', right: '5%', bottom: '15%' },
    };
  };

  const tradeColumns = [
    { title: '日期', dataIndex: 'date', key: 'date', width: 100 },
    { title: '股票代码', dataIndex: 'code', key: 'code', width: 110 },
    {
      title: '方向',
      dataIndex: 'direction',
      key: 'direction',
      width: 70,
      render: (direction: string) => (
        <Tag color={direction === 'buy' ? 'success' : 'error'}>
          {direction === 'buy' ? '买入' : '卖出'}
        </Tag>
      ),
    },
    { title: '数量', dataIndex: 'amount', key: 'amount', width: 90, align: 'right' as const },
    { title: '价格', dataIndex: 'price', key: 'price', width: 90, align: 'right' as const },
    { title: '金额', dataIndex: 'cost', key: 'cost', width: 100, align: 'right' as const },
  ];

  const positionColumns = [
    {
      title: '股票代码',
      key: 'code',
      width: 110,
      render: (record: PositionData) => record.contract_code || record.code || 'N/A',
    },
    {
      title: '数量',
      key: 'volume',
      width: 90,
      align: 'right' as const,
      render: (record: PositionData) => record.position || record.volume || 0,
    },
    {
      title: '成本价',
      key: 'cost',
      width: 90,
      align: 'right' as const,
      render: (record: PositionData) =>
        ((record.avg_price ?? record.cost_price ?? 0) || 0).toFixed(2),
    },
    {
      title: '当前价',
      key: 'current',
      width: 90,
      align: 'right' as const,
      render: (record: PositionData) =>
        ((record.now_price ?? record.current_price ?? 0) || 0).toFixed(2),
    },
    {
      title: '盈亏',
      key: 'profit',
      width: 100,
      align: 'right' as const,
      render: (record: PositionData) => {
        const profit = (record.profit ?? 0) || 0;
        return (
          <span style={{ color: profit >= 0 ? '#52c41a' : '#ff4d4f' }}>
            {profit.toFixed(2)}
          </span>
        );
      },
    },
    {
      title: '日期',
      key: 'date',
      width: 100,
      render: (record: PositionData) => record.date || record.gmt_create || 'N/A',
    },
  ];

  const latestAccount = accountData.length > 0 ? accountData[accountData.length - 1] : null;

  // 计算关键绩效指标
  const calculateMetrics = () => {
    if (profitData.length === 0) {
      return {
        totalReturn: 0,
        annualReturn: 0,
        maxDrawdown: 0,
        sharpeRatio: 0,
        winRate: 0,
        totalTrades: tradeData.length,
      };
    }

    const initialCapital = (config.start_capital || 1000) * 10000;
    const equity = profitData.map((item) => {
      const totalAsset = item.total_value ?? item.total_profit ?? item.strategy_profit ?? 0;
      return Number(totalAsset) || 0;
    });

    // 总收益率
    const latestValue = equity[equity.length - 1];
    const totalReturn = ((latestValue - initialCapital) / initialCapital) * 100;

    // 年化收益率（简化计算）
    const days = profitData.length;
    const annualReturn = totalReturn * (252 / Math.max(days, 1));

    // 最大回撤
    let maxDrawdown = 0;
    let peak = equity[0];
    for (const value of equity) {
      if (value > peak) peak = value;
      const drawdown = ((peak - value) / peak) * 100;
      if (drawdown > maxDrawdown) maxDrawdown = drawdown;
    }

    // 夏普比率（简化计算）
    const returns = equity.slice(1).map((v, i) => (v - equity[i]) / equity[i]);
    const avgReturn = returns.reduce((a, b) => a + b, 0) / returns.length;
    const stdReturn = Math.sqrt(
      returns.reduce((sum, r) => sum + Math.pow(r - avgReturn, 0), 0) / returns.length
    );
    const sharpeRatio = stdReturn > 0 ? (avgReturn / stdReturn) * Math.sqrt(252) : 0;

    // 胜率
    const profitTrades = tradeData.filter((t) => (t.profit ?? 0) > 0).length;
    const winRate = tradeData.length > 0 ? (profitTrades / tradeData.length) * 100 : 0;

    return {
      totalReturn,
      annualReturn,
      maxDrawdown,
      sharpeRatio,
      winRate,
      totalTrades: tradeData.length,
    };
  };

  const metrics = calculateMetrics();

  // 获取回撤曲线数据
  const getDrawdownChartOption = () => {
    const initialCapital = (config.start_capital || 1000) * 10000;
    const equity = profitData.map((item) => {
      const totalAsset = item.total_value ?? item.total_profit ?? item.strategy_profit ?? 0;
      return Number(totalAsset) || initialCapital;
    });

    const dates = profitData.map((item) => {
      const date = item.date || item.gmt_create_time || item.gmt_create || '';
      return String(date).substring(0, 8);
    });

    // 计算回撤序列
    const drawdowns: number[] = [];
    let peak = equity[0];
    for (const value of equity) {
      if (value > peak) peak = value;
      const drawdown = ((peak - value) / peak) * 100;
      drawdowns.push(-drawdown);
    }

    return {
      title: {
        text: '回撤曲线',
        left: 'center',
        textStyle: { fontSize: 14, fontWeight: 'normal' },
      },
      tooltip: {
        trigger: 'axis',
        formatter: (params: any) => {
          if (!params || !params[0]) return '';
          const drawdown = Math.abs(params[0].value);
          return params[0].name + '<br/>' + params[0].marker + '回撤: ' + drawdown.toFixed(2) + '%';
        },
      },
      xAxis: {
        type: 'category',
        data: dates,
        axisLabel: { rotate: 45, interval: Math.floor(dates.length / 10) },
      },
      yAxis: {
        type: 'value',
        name: '回撤 (%)',
        axisLabel: { formatter: '{value}%' },
      },
      series: [
        {
          name: '回撤',
          type: 'line',
          data: drawdowns,
          smooth: true,
          lineStyle: { color: '#ff4d4f', width: 2 },
          areaStyle: {
            color: {
              type: 'linear',
              x: 0,
              y: 0,
              x2: 0,
              y2: 1,
              colorStops: [
                { offset: 0, color: 'rgba(255, 77, 79, 0.3)' },
                { offset: 1, color: 'rgba(255, 77, 79, 0.05)' },
              ],
            },
          },
        },
      ],
      grid: { left: '10%', right: '5%', bottom: '15%' },
    };
  };

  return (
    <div style={{ padding: '20px', background: '#f0f2f5', minHeight: '100vh' }}>
      {/* 回测进度条（如果正在运行） */}
      {(backtesting || (currentBacktestId && backtestStatus === 'running')) && (
        <Card style={{ marginBottom: 16 }}>
          <Row align="middle" gutter={16}>
            <Col flex="auto">
              <Progress
                percent={backtestProgress}
                status={
                  backtestStatus === 'completed'
                    ? 'success'
                    : backtestStatus === 'failed'
                    ? 'exception'
                    : 'active'
                }
              />
              <p style={{ marginTop: 8, marginBottom: 0, color: '#666' }}>
                状态: {getStatusText(backtestStatus)} {currentBacktestId && `(ID: ${currentBacktestId})`}
              </p>
            </Col>
            <Col>
              <Space>
              {currentBacktestId && (
                  <Button size="small" onClick={onLoadResults}>
                    {backtestStatus === 'completed' ? '刷新结果' : '强制加载'}
                  </Button>
                )}
                {currentBacktestId && backtestStatus === 'running' && (
                  <Button size="small" type="primary" onClick={onManualComplete}>
                    标记完成
                  </Button>
                )}
              </Space>
            </Col>
          </Row>
        </Card>
      )}

      {/* 顶部：关键绩效指标卡片 */}
      {!currentBacktestId && (
        <Card style={{ marginBottom: 16 }}>
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description="暂无回测数据，请先配置参数并运行回测。以下显示默认空状态界面。"
            style={{ padding: '20px 0' }}
          />
        </Card>
      )}
      
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
            <Col span={4}>
              <Card>
                <Statistic
                  title="累计收益率"
                  value={metrics.totalReturn}
                  precision={2}
                  suffix="%"
                  valueStyle={{ color: metrics.totalReturn >= 0 ? '#3f8600' : '#cf1322', fontSize: 24 }}
                  prefix={metrics.totalReturn >= 0 ? <RiseOutlined /> : <FallOutlined />}
                />
              </Card>
            </Col>
            <Col span={4}>
              <Card>
                        <Statistic
                  title="年化收益率"
                  value={metrics.annualReturn}
                          precision={2}
                  suffix="%"
                  valueStyle={{ fontSize: 24 }}
                        />
              </Card>
                      </Col>
            <Col span={4}>
              <Card>
                        <Statistic
                  title="最大回撤"
                  value={metrics.maxDrawdown}
                          precision={2}
                  suffix="%"
                  valueStyle={{ color: '#cf1322', fontSize: 24 }}
                        />
              </Card>
                      </Col>
            <Col span={4}>
              <Card>
                        <Statistic
                  title="夏普比率"
                  value={metrics.sharpeRatio}
                          precision={2}
                  valueStyle={{ fontSize: 24 }}
                        />
              </Card>
                      </Col>
            <Col span={4}>
              <Card>
                <Statistic
                  title="胜率"
                  value={metrics.winRate}
                  precision={2}
                  suffix="%"
                  valueStyle={{ fontSize: 24 }}
                />
                </Card>
            </Col>
            <Col span={4}>
              <Card>
                <Statistic
                  title="总交易次数"
                  value={metrics.totalTrades}
                  valueStyle={{ fontSize: 24 }}
                />
            </Card>
            </Col>
          </Row>

          {/* 中部：图表区域 */}
          <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
            <Col span={16}>
            <Card
                title={
                  <Space>
                    <LineChartOutlined />
                    <span>策略净值曲线</span>
                  </Space>
                }
              extra={
                <Button size="small" icon={<ReloadOutlined />} onClick={onLoadResults}>
                    刷新
                </Button>
              }
            >
                {profitData.length > 0 ? (
                  <ReactECharts ref={chartRef} option={getChartOption()} style={{ height: 450 }} />
                ) : (
                  <Empty description="暂无收益数据" />
                )}
            </Card>
            </Col>
            <Col span={8}>
              <Card
                title={
                  <Space>
                    <BarChartOutlined />
                    <span>回撤分析</span>
                  </Space>
                }
              >
                {profitData.length > 0 ? (
                  <ReactECharts option={getDrawdownChartOption()} style={{ height: 450 }} />
                ) : (
                  <Empty description="暂无回撤数据" />
                )}
              </Card>
            </Col>
          </Row>

          {/* 底部：详细数据标签页 */}
          <Card>
            <Tabs defaultActiveKey="1" size="large">
              <TabPane
                tab={
                  <span>
                    <FundOutlined />
                    账户信息
                  </span>
                }
                key="1"
              >
                {latestAccount ? (
                  <div>
                    <Descriptions title="最新账户状态" bordered column={3} size="small">
                      <Descriptions.Item label="总资产">
                        {(latestAccount.total_profit ?? 0).toLocaleString('zh-CN', {
                          minimumFractionDigits: 2,
                          maximumFractionDigits: 2,
                        })}
                      </Descriptions.Item>
                      <Descriptions.Item label="可用资金">
                        {(latestAccount.available_funds ?? 0).toLocaleString('zh-CN', {
                          minimumFractionDigits: 2,
                          maximumFractionDigits: 2,
                        })}
                      </Descriptions.Item>
                      <Descriptions.Item label="持仓市值">
                        {(latestAccount.market_value ?? 0).toLocaleString('zh-CN', {
                          minimumFractionDigits: 2,
                          maximumFractionDigits: 2,
                        })}
                      </Descriptions.Item>
                      <Descriptions.Item label="更新时间" span={3}>
                        {latestAccount.gmt_create || 'N/A'}
                      </Descriptions.Item>
                    </Descriptions>
                    <Divider />
                    <Row gutter={16}>
                      <Col span={6}>
                        <Statistic title="账户记录数" value={dataStats.accountCount} />
                      </Col>
                      <Col span={6}>
                        <Statistic title="交易记录数" value={dataStats.tradeCount} />
                      </Col>
                      <Col span={6}>
                        <Statistic title="持仓记录数" value={dataStats.positionCount} />
                      </Col>
                      <Col span={6}>
                        <Statistic title="收益记录数" value={dataStats.profitCount} />
                      </Col>
                    </Row>
                  </div>
                ) : (
                  <Empty description="暂无账户数据" />
                )}
              </TabPane>

              <TabPane
                tab={
                  <span>
                    <TransactionOutlined />
                    成交明细 ({tradeData.length})
                  </span>
                }
                key="2"
              >
                {tradeData.length > 0 ? (
              <Table
                columns={tradeColumns}
                dataSource={tradeData}
                    pagination={{ pageSize: 20, showSizeChanger: true, showTotal: (total) => `共 ${total} 条` }}
                    size="small"
                    scroll={{ x: 800 }}
                    rowKey={(_record, index) => index?.toString() || '0'}
                  />
                ) : (
                  <Empty description="暂无交易记录" />
                )}
              </TabPane>

              <TabPane
                tab={
                  <span>
                    <FundOutlined />
                    持仓详情 ({positionData.length})
                  </span>
                }
                key="3"
              >
                {positionData.length > 0 ? (
                  <Table
                    columns={positionColumns}
                    dataSource={positionData}
                    pagination={{ pageSize: 20, showSizeChanger: true, showTotal: (total) => `共 ${total} 条` }}
                    size="small"
                    scroll={{ x: 800 }}
                    rowKey={(_record, index) => index?.toString() || '0'}
                  />
                ) : (
                  <Empty description="暂无持仓记录" />
                )}
              </TabPane>

              <TabPane
                tab={
                  <span>
                    <BarChartOutlined />
                    回测配置
                  </span>
                }
                key="4"
              >
                <Row gutter={16}>
                  <Col span={12}>
                    <Card title="基本配置" size="small">
                      <Descriptions bordered column={1} size="small">
                        <Descriptions.Item label="策略名称">{strategyName || 'N/A'}</Descriptions.Item>
                        <Descriptions.Item label="初始资金">{config.start_capital} 万</Descriptions.Item>
                        <Descriptions.Item label="佣金费率">{config.commission_rate} ‰</Descriptions.Item>
                        <Descriptions.Item label="开始日期">{config.start_date}</Descriptions.Item>
                        <Descriptions.Item label="结束日期">{config.end_date}</Descriptions.Item>
                        <Descriptions.Item label="数据频率">{config.frequency}</Descriptions.Item>
                        <Descriptions.Item label="基准指数">{config.standard_symbol}</Descriptions.Item>
                      </Descriptions>
            </Card>
      </Col>
                  <Col span={12}>
                    <Card title="编辑配置" size="small">
          <Form layout="vertical" size="small">
            <Form.Item label="策略名称">
              <Input
                value={strategyName}
                onChange={(e) => onStrategyNameChange(e.target.value)}
                placeholder="请输入策略名称"
              />
            </Form.Item>
            <Form.Item label="初始资金(万)">
              <InputNumber
                style={{ width: '100%' }}
                min={1}
                max={100000}
                value={config.start_capital}
                onChange={(value) => onConfigChange({ ...config, start_capital: value || 1000 })}
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
                onChange={(value) => onConfigChange({ ...config, commission_rate: value || 1 })}
              />
            </Form.Item>
                        <Row gutter={8}>
                          <Col span={12}>
            <Form.Item label="开始日期">
              <Input
                value={config.start_date}
                onChange={(e) => onConfigChange({ ...config, start_date: e.target.value })}
                placeholder="YYYYMMDD"
              />
            </Form.Item>
                          </Col>
                          <Col span={12}>
            <Form.Item label="结束日期">
              <Input
                value={config.end_date}
                onChange={(e) => onConfigChange({ ...config, end_date: e.target.value })}
                placeholder="YYYYMMDD"
              />
            </Form.Item>
                          </Col>
                        </Row>
                        <Row gutter={8}>
                          <Col span={12}>
            <Form.Item label="数据频率">
              <Select
                value={config.frequency}
                onChange={(value) => onConfigChange({ ...config, frequency: value })}
              >
                <Select.Option value="1d">日线</Select.Option>
                <Select.Option value="1m">分钟线</Select.Option>
              </Select>
            </Form.Item>
                          </Col>
                          <Col span={12}>
            <Form.Item label="基准指数">
              <Select
                value={config.standard_symbol}
                onChange={(value) => onConfigChange({ ...config, standard_symbol: value })}
              >
                <Select.Option value="000001.SH">上证指数</Select.Option>
                <Select.Option value="000300.SH">沪深300</Select.Option>
                <Select.Option value="000905.SH">中证500</Select.Option>
              </Select>
            </Form.Item>
                          </Col>
                        </Row>
          </Form>
        </Card>
      </Col>
    </Row>
              </TabPane>
            </Tabs>
          </Card>
    </div>
  );
};

export default BacktestResults;

