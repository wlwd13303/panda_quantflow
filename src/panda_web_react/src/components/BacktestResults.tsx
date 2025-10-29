import React, { useEffect, useRef, useState } from 'react';
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
} from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import type {
  ProfitData,
  TradeData,
  PositionData,
  AccountData,
  DataStats,
  BacktestConfig,
} from '@/types';

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

    const equity = profitData.map((item) => {
      const value =
        item.total_value ?? item.total_profit ?? item.csi_stock ?? item.strategy_profit ?? 0;
      return Number(value) || 0;
    });

    return {
      title: {
        text: '资产净值曲线',
        left: 'center',
      },
      tooltip: {
        trigger: 'axis',
        formatter: (params: any) => {
          if (!params || !params[0]) return '';
          const value = params[0].value ?? 0;
          const numValue = Number(value);
          return (
            params[0].name +
            '<br/>' +
            params[0].marker +
            '净值: ' +
            (isNaN(numValue) ? '0.00' : numValue.toFixed(2))
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
        name: '资产净值',
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

  return (
    <Row gutter={[16, 16]} style={{ padding: '20px' }}>
      {/* 左侧：图表和列表 */}
      <Col span={16}>
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          {/* 回测进度 */}
          {(backtesting || currentBacktestId) && (
            <Card
              title="回测进度"
              extra={
                <Space>
                  {currentBacktestId && (
                    <Button size="small" onClick={onLoadResults}>
                      {backtestStatus === 'completed' ? '刷新结果' : '强制加载结果'}
                    </Button>
                  )}
                  {currentBacktestId && backtestStatus === 'running' && (
                    <Button size="small" type="primary" onClick={onManualComplete}>
                      手动标记完成
                    </Button>
                  )}
                </Space>
              }
            >
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
              <p style={{ marginTop: 10, color: '#666' }}>状态: {getStatusText(backtestStatus)}</p>
              {currentBacktestId && (
                <p style={{ marginTop: 5, color: '#909399', fontSize: 12 }}>
                  回测ID: {currentBacktestId}
                </p>
              )}

              {/* 实时数据统计 */}
              {currentBacktestId &&
                (dataStats.accountCount > 0 || dataStats.tradeCount > 0) && (
                  <Row gutter={16} style={{ marginTop: 15 }}>
                    <Col span={6}>
                      <Statistic title="账户记录" value={dataStats.accountCount} />
                    </Col>
                    <Col span={6}>
                      <Statistic title="交易记录" value={dataStats.tradeCount} />
                    </Col>
                    <Col span={6}>
                      <Statistic title="持仓记录" value={dataStats.positionCount} />
                    </Col>
                    <Col span={6}>
                      <Statistic title="收益记录" value={dataStats.profitCount} />
                    </Col>
                  </Row>
                )}

              {/* 最新账户状态 */}
              {latestAccount && (
                <Card
                  size="small"
                  style={{
                    marginTop: 15,
                    background: '#e8f4fd',
                    borderLeft: '4px solid #1890ff',
                  }}
                >
                  <div style={{ fontWeight: 'bold', color: '#1890ff', marginBottom: 10 }}>
                    💰 最新账户状态
                  </div>
                  <Row gutter={16}>
                    {latestAccount.total_profit !== undefined && (
                      <Col span={8}>
                        <Statistic
                          title="总资产"
                          value={latestAccount.total_profit}
                          precision={2}
                        />
                      </Col>
                    )}
                    {latestAccount.available_funds !== undefined && (
                      <Col span={8}>
                        <Statistic
                          title="可用资金"
                          value={latestAccount.available_funds}
                          precision={2}
                        />
                      </Col>
                    )}
                    {latestAccount.market_value !== undefined && (
                      <Col span={8}>
                        <Statistic
                          title="持仓市值"
                          value={latestAccount.market_value}
                          precision={2}
                        />
                      </Col>
                    )}
                  </Row>
                  {latestAccount.gmt_create && (
                    <p style={{ marginTop: 10, fontSize: 12, color: '#666' }}>
                      更新时间: {latestAccount.gmt_create}
                    </p>
                  )}
                </Card>
              )}
            </Card>
          )}

          {/* 资产曲线图 */}
          {currentBacktestId && profitData.length > 0 && (
            <Card
              title="资产净值曲线"
              extra={
                <Button size="small" icon={<ReloadOutlined />} onClick={onLoadResults}>
                  刷新图表
                </Button>
              }
            >
              <ReactECharts ref={chartRef} option={getChartOption()} style={{ height: 400 }} />
            </Card>
          )}

          {/* 持仓信息 */}
          {currentBacktestId && positionData.length > 0 && (
            <Card title="当前持仓 (最近20条)">
              <Table
                columns={positionColumns}
                dataSource={positionData.slice(-20)}
                pagination={false}
                size="small"
                scroll={{ y: 300 }}
                rowKey={(record, index) => index?.toString() || '0'}
              />
            </Card>
          )}

          {/* 成交订单 */}
          {currentBacktestId && tradeData.length > 0 && (
            <Card title="成交订单 (前50条)">
              <Table
                columns={tradeColumns}
                dataSource={tradeData}
                pagination={false}
                size="small"
                scroll={{ y: 400 }}
                rowKey={(record, index) => index?.toString() || '0'}
              />
            </Card>
          )}

          {/* 无数据提示 */}
          {!currentBacktestId && (
            <Card>
              <Empty description="暂无回测数据，请先运行回测" />
            </Card>
          )}
        </Space>
      </Col>

      {/* 右侧：参数配置 */}
      <Col span={8}>
        <Card title="回测参数配置">
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

            <Form.Item label="开始日期">
              <Input
                value={config.start_date}
                onChange={(e) => onConfigChange({ ...config, start_date: e.target.value })}
                placeholder="YYYYMMDD"
              />
            </Form.Item>

            <Form.Item label="结束日期">
              <Input
                value={config.end_date}
                onChange={(e) => onConfigChange({ ...config, end_date: e.target.value })}
                placeholder="YYYYMMDD"
              />
            </Form.Item>

            <Form.Item label="数据频率">
              <Select
                value={config.frequency}
                onChange={(value) => onConfigChange({ ...config, frequency: value })}
              >
                <Select.Option value="1d">日线</Select.Option>
                <Select.Option value="1m">分钟线</Select.Option>
              </Select>
            </Form.Item>

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
          </Form>
        </Card>
      </Col>
    </Row>
  );
};

export default BacktestResults;

