import React, { useState, useEffect, useRef } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Table,
  Alert,
  Button,
  Space,
  Tag,
  Spin,
  Empty,
  Progress,
  InputNumber,
  Select,
} from 'antd';
import {
  ReloadOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  RiseOutlined,
  FallOutlined,
} from '@ant-design/icons';
import { backtestApi } from '@/services/api';
import type { BacktestMonitorData, BacktestRecord } from '@/types';

interface BacktestMonitorProps {
  initialBacktestId?: string;
}

const BacktestMonitor: React.FC<BacktestMonitorProps> = ({ initialBacktestId }) => {
  const [backId, setBackId] = useState<string>(initialBacktestId || '');
  const [monitorData, setMonitorData] = useState<BacktestMonitorData | null>(null);
  const [loading, setLoading] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [refreshInterval, setRefreshInterval] = useState(2000); // 2秒
  const [backtestList, setBacktestList] = useState<BacktestRecord[]>([]);
  const [error, setError] = useState<string | null>(null);

  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const previousStatsRef = useRef<any>(null);

  // 加载回测列表
  const loadBacktestList = async () => {
    try {
      const result = await backtestApi.getBacktestList(1, 20);
      setBacktestList(result.items || []);

      // 如果没有指定初始ID，使用第一个运行中的回测
      if (!initialBacktestId && result.items && result.items.length > 0) {
        const runningBacktest = result.items.find(bt => bt.status === 'running');
        if (runningBacktest) {
          setBackId(runningBacktest._id || runningBacktest.run_id || '');
        } else if (result.items[0]) {
          setBackId(result.items[0]._id || result.items[0].run_id || '');
        }
      }
    } catch (error: any) {
      console.error('加载回测列表失败:', error);
    }
  };

  // 获取监控数据
  const fetchMonitorData = async () => {
    if (!backId) {
      setError('请选择要监控的回测');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const data = await backtestApi.getMonitorData(backId);

      if (data.success) {
        // 保存之前的统计数据
        if (monitorData?.stats) {
          previousStatsRef.current = monitorData.stats;
        }
        setMonitorData(data);
        setError(null);
      } else {
        setError(data.error || '获取监控数据失败');
      }
    } catch (err: any) {
      console.error('获取监控数据失败:', err);
      setError(err.message || '获取监控数据失败');
    } finally {
      setLoading(false);
    }
  };

  // 初始化
  useEffect(() => {
    loadBacktestList();
  }, []);

  // 设置自动刷新
  useEffect(() => {
    if (autoRefresh && backId) {
      fetchMonitorData();
      timerRef.current = setInterval(fetchMonitorData, refreshInterval);
    } else {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    }

    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, [autoRefresh, backId, refreshInterval]);

  // 计算数据增量
  const getIncrement = (current: number, fieldName: string) => {
    if (!previousStatsRef.current) return 0;
    const previous = previousStatsRef.current[fieldName] || 0;
    return current - previous;
  };

  // 格式化数字
  const formatNumber = (num?: number, decimals: number = 2) => {
    if (num === undefined || num === null || isNaN(num)) return '-';
    return num.toLocaleString('zh-CN', {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    });
  };

  // 渲染净值曲线（简化版ASCII图）
  const renderEquityCurve = () => {
    if (!monitorData?.equity_curve || monitorData.equity_curve.length < 2) {
      return <Empty description="暂无净值数据" />;
    }

    const data = monitorData.equity_curve.filter(d => d.value !== undefined && d.value !== null);
    if (data.length < 2) {
      return <Empty description="净值数据不足" />;
    }

    const values = data.map(d => d.value!);
    const minValue = Math.min(...values);
    const maxValue = Math.max(...values);
    const range = maxValue - minValue;

    const currentValue = values[values.length - 1];
    const previousValue = values.length > 1 ? values[values.length - 2] : currentValue;
    const change = currentValue - previousValue;
    const changePercent = previousValue !== 0 ? (change / previousValue) * 100 : 0;

    return (
      <div style={{ padding: '10px' }}>
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={8}>
            <Statistic
              title="当前净值"
              value={currentValue}
              precision={2}
              valueStyle={{ color: change >= 0 ? '#3f8600' : '#cf1322' }}
            />
          </Col>
          <Col span={8}>
            <Statistic
              title="净值变化"
              value={change}
              precision={2}
              prefix={change >= 0 ? <RiseOutlined /> : <FallOutlined />}
              valueStyle={{ color: change >= 0 ? '#3f8600' : '#cf1322' }}
            />
          </Col>
          <Col span={8}>
            <Statistic
              title="变化率"
              value={changePercent}
              precision={2}
              suffix="%"
              valueStyle={{ color: changePercent >= 0 ? '#3f8600' : '#cf1322' }}
            />
          </Col>
        </Row>

        <div style={{
          background: '#f5f5f5',
          padding: '20px',
          borderRadius: '4px',
          fontFamily: 'monospace',
          fontSize: '12px',
          lineHeight: '16px',
          overflowX: 'auto',
        }}>
          {/* 简化的图表展示 */}
          <div>数据点数: {data.length}</div>
          <div>最高: {formatNumber(maxValue)}</div>
          <div>最低: {formatNumber(minValue)}</div>
          <div>波动: {formatNumber(range)}</div>

          {/* 趋势指示器 */}
          <div style={{ marginTop: 10 }}>
            <Progress
              percent={range > 0 ? ((currentValue - minValue) / range * 100) : 50}
              showInfo={false}
              strokeColor={change >= 0 ? '#52c41a' : '#ff4d4f'}
            />
            <div style={{ fontSize: '10px', color: '#999', marginTop: 4 }}>
              {data[0]?.date} 至 {data[data.length - 1]?.date}
            </div>
          </div>
        </div>
      </div>
    );
  };

  // 交易记录列
  const tradeColumns = [
    {
      title: '日期',
      dataIndex: 'date',
      key: 'date',
      width: 100,
    },
    {
      title: '时间',
      dataIndex: 'time',
      key: 'time',
      width: 80,
    },
    {
      title: '股票代码',
      dataIndex: 'symbol',
      key: 'symbol',
      width: 120,
    },
    {
      title: '方向',
      dataIndex: 'direction',
      key: 'direction',
      width: 80,
      render: (direction: string, record: any) => {
        const isBuy = record.side === 0 || direction === '买入';
        return (
          <Tag color={isBuy ? 'green' : 'red'}>
            {direction || (isBuy ? '买入' : '卖出')}
          </Tag>
        );
      },
    },
    {
      title: '价格',
      dataIndex: 'price',
      key: 'price',
      width: 100,
      align: 'right' as const,
      render: (val: number) => formatNumber(val),
    },
    {
      title: '数量',
      dataIndex: 'volume',
      key: 'volume',
      width: 100,
      align: 'right' as const,
      render: (val: number) => formatNumber(val, 0),
    },
    {
      title: '成交额',
      dataIndex: 'amount',
      key: 'amount',
      width: 120,
      align: 'right' as const,
      render: (val: number) => formatNumber(val),
    },
  ];

  // 持仓列
  const positionColumns = [
    {
      title: '股票代码',
      dataIndex: 'symbol',
      key: 'symbol',
      width: 120,
    },
    {
      title: '持仓量',
      dataIndex: 'volume',
      key: 'volume',
      width: 100,
      align: 'right' as const,
      render: (val: number) => formatNumber(val, 0),
    },
    {
      title: '市值',
      dataIndex: 'market_value',
      key: 'market_value',
      width: 120,
      align: 'right' as const,
      render: (val: number) => formatNumber(val),
    },
    {
      title: '盈亏',
      dataIndex: 'profit',
      key: 'profit',
      width: 120,
      align: 'right' as const,
      render: (val: number) => (
        <span style={{ color: val >= 0 ? '#3f8600' : '#cf1322' }}>
          {formatNumber(val)}
        </span>
      ),
    },
    {
      title: '收益率',
      dataIndex: 'profit_rate',
      key: 'profit_rate',
      width: 100,
      align: 'right' as const,
      render: (val: number) => (
        <span style={{ color: val >= 0 ? '#3f8600' : '#cf1322' }}>
          {formatNumber(val * 100, 2)}%
        </span>
      ),
    },
  ];

  const stats = monitorData?.stats;
  const latestAccount = monitorData?.latest_account;

  return (
    <div style={{ padding: 20 }}>
      <Card
        title={
          <Space>
            <span style={{ fontSize: 18, fontWeight: 'bold' }}>📊 回测实时监控</span>
            {monitorData?.status && (
              <Tag color={monitorData.status === 'running' ? 'processing' : 'success'}>
                {monitorData.status === 'running' ? '运行中' : '已完成'}
              </Tag>
            )}
          </Space>
        }
        extra={
          <Space>
            <span>回测ID:</span>
            <Select
              style={{ width: 250 }}
              value={backId}
              onChange={setBackId}
              placeholder="选择回测"
              showSearch
              optionFilterProp="children"
            >
              {backtestList.map((bt) => (
                <Select.Option key={bt._id || bt.run_id} value={bt._id || bt.run_id || ''}>
                  {bt.strategy_name} - {bt._id || bt.run_id}
                </Select.Option>
              ))}
            </Select>

            <span>刷新间隔:</span>
            <InputNumber
              min={1}
              max={60}
              value={refreshInterval / 1000}
              onChange={(val) => setRefreshInterval((val || 2) * 1000)}
              style={{ width: 80 }}
              suffix="秒"
            />

            <Button
              type={autoRefresh ? 'primary' : 'default'}
              icon={autoRefresh ? <PauseCircleOutlined /> : <PlayCircleOutlined />}
              onClick={() => setAutoRefresh(!autoRefresh)}
            >
              {autoRefresh ? '暂停' : '开始'}
            </Button>

            <Button
              icon={<ReloadOutlined />}
              onClick={fetchMonitorData}
              loading={loading}
            >
              刷新
            </Button>
          </Space>
        }
      >
        {error && (
          <Alert
            message="错误"
            description={error}
            type="error"
            closable
            onClose={() => setError(null)}
            style={{ marginBottom: 16 }}
          />
        )}

        {loading && !monitorData && (
          <div style={{ textAlign: 'center', padding: 50 }}>
            <Spin size="large" />
            <div style={{ marginTop: 16 }}>加载监控数据中...</div>
          </div>
        )}

        {!loading && !monitorData && !error && (
          <Empty description="请选择回测并点击刷新开始监控" />
        )}

        {monitorData && (
          <>
            {/* 进度条 */}
            {monitorData.progress !== undefined && monitorData.status === 'running' && (
              <div style={{ marginBottom: 20 }}>
                <Progress percent={Math.round(monitorData.progress)} status="active" />
              </div>
            )}

            {/* 数据统计 */}
            <Row gutter={16} style={{ marginBottom: 24 }}>
              <Col span={6}>
                <Card>
                  <Statistic
                    title="账户数据"
                    value={stats?.account_count || 0}
                    suffix="条"
                    prefix={getIncrement(stats?.account_count || 0, 'account_count') > 0 ? `(+${getIncrement(stats?.account_count || 0, 'account_count')})` : ''}
                  />
                </Card>
              </Col>
              <Col span={6}>
                <Card>
                  <Statistic
                    title="交易记录"
                    value={stats?.trade_count || 0}
                    suffix="条"
                    prefix={getIncrement(stats?.trade_count || 0, 'trade_count') > 0 ? `(+${getIncrement(stats?.trade_count || 0, 'trade_count')})` : ''}
                  />
                </Card>
              </Col>
              <Col span={6}>
                <Card>
                  <Statistic
                    title="持仓记录"
                    value={stats?.position_count || 0}
                    suffix="条"
                    prefix={getIncrement(stats?.position_count || 0, 'position_count') > 0 ? `(+${getIncrement(stats?.position_count || 0, 'position_count')})` : ''}
                  />
                </Card>
              </Col>
              <Col span={6}>
                <Card>
                  <Statistic
                    title="收益记录"
                    value={stats?.profit_count || 0}
                    suffix="条"
                    prefix={getIncrement(stats?.profit_count || 0, 'profit_count') > 0 ? `(+${getIncrement(stats?.profit_count || 0, 'profit_count')})` : ''}
                  />
                </Card>
              </Col>
            </Row>

            {/* 最新账户状态 */}
            {latestAccount && (
              <Card title="💰 最新账户状态" style={{ marginBottom: 24 }}>
                <Row gutter={16}>
                  <Col span={4}>
                    <Statistic
                      title="日期"
                      value={latestAccount.date || '-'}
                      valueStyle={{ fontSize: 16 }}
                    />
                  </Col>
                  <Col span={5}>
                    <Statistic
                      title="总资产"
                      value={latestAccount.total_asset}
                      precision={2}
                      valueStyle={{ color: '#1890ff' }}
                    />
                  </Col>
                  <Col span={5}>
                    <Statistic
                      title="可用资金"
                      value={latestAccount.available}
                      precision={2}
                    />
                  </Col>
                  <Col span={5}>
                    <Statistic
                      title="持仓市值"
                      value={latestAccount.market_value}
                      precision={2}
                    />
                  </Col>
                  <Col span={5}>
                    <Statistic
                      title="收益率"
                      value={latestAccount.profit_rate ? latestAccount.profit_rate * 100 : 0}
                      precision={2}
                      suffix="%"
                      valueStyle={{
                        color: (latestAccount.profit_rate || 0) >= 0 ? '#3f8600' : '#cf1322',
                      }}
                      prefix={
                        (latestAccount.profit_rate || 0) >= 0 ? <RiseOutlined /> : <FallOutlined />
                      }
                    />
                  </Col>
                </Row>
              </Card>
            )}

            {/* 净值曲线 */}
            <Card title="📉 净值曲线" style={{ marginBottom: 24 }}>
              {renderEquityCurve()}
            </Card>

            {/* 最近交易 */}
            <Card title="🔄 最近5笔交易" style={{ marginBottom: 24 }}>
              <Table
                columns={tradeColumns}
                dataSource={monitorData.recent_trades || []}
                pagination={false}
                size="small"
                rowKey={(record, index) => `${record.date}_${record.time}_${index}`}
                locale={{ emptyText: '暂无交易记录' }}
              />
            </Card>

            {/* 最新持仓 */}
            <Card title="📊 最新持仓">
              <Table
                columns={positionColumns}
                dataSource={monitorData.latest_positions || []}
                pagination={false}
                size="small"
                rowKey={(record) => record.symbol || ''}
                locale={{ emptyText: '暂无持仓' }}
              />
              {monitorData.latest_positions && monitorData.latest_positions.length > 0 && (
                <div style={{ marginTop: 10, color: '#999', fontSize: 12 }}>
                  共 {monitorData.latest_positions.length} 只持仓
                </div>
              )}
            </Card>
          </>
        )}
      </Card>
    </div>
  );
};

export default BacktestMonitor;

