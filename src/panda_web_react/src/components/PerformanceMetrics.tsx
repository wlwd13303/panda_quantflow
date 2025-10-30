import React from 'react';
import { Card, Row, Col, Typography, Progress, Space, Tag, Alert } from 'antd';
import {
  RiseOutlined,
  FallOutlined,
  TrophyOutlined,
  SafetyOutlined,
  ThunderboltOutlined,
  LineChartOutlined,
} from '@ant-design/icons';
import type { ProfitData } from '@/types';

const { Title, Text } = Typography;

interface PerformanceMetricsProps {
  profitData: ProfitData[];
  config: {
    start_capital: number;
    start_date: string;
    end_date: string;
  };
}

interface Metrics {
  // 收益相关
  totalReturn: number;
  totalReturnRate: number;
  annualizedReturn: number;
  
  // 风险相关
  volatility: number;
  sharpeRatio: number;
  maxDrawdown: number;
  maxDrawdownRate: number;
  
  // 交易相关
  winRate: number;
  profitLossRatio: number;
  
  // 对比相关
  alpha: number;
  beta: number;
  excessReturn: number;
  excessReturnRate: number;
}

const PerformanceMetrics: React.FC<PerformanceMetricsProps> = ({ profitData, config }) => {
  // 计算各项指标
  const calculateMetrics = (): Metrics => {
    if (!profitData || profitData.length === 0) {
      return {
        totalReturn: 0,
        totalReturnRate: 0,
        annualizedReturn: 0,
        volatility: 0,
        sharpeRatio: 0,
        maxDrawdown: 0,
        maxDrawdownRate: 0,
        winRate: 0,
        profitLossRatio: 0,
        alpha: 0,
        beta: 0,
        excessReturn: 0,
        excessReturnRate: 0,
      };
    }

    const initialCapital = config.start_capital * 10000; // 转换为元
    
    // 获取资产净值序列
    const equityCurve = profitData.map(item => 
      Number(item.total_value ?? item.total_profit ?? item.strategy_profit ?? initialCapital)
    );
    
    const finalEquity = equityCurve[equityCurve.length - 1];
    const totalReturn = finalEquity - initialCapital;
    const totalReturnRate = (totalReturn / initialCapital) * 100;
    
    // 计算年化收益率
    const tradingDays = profitData.length;
    const years = tradingDays / 252; // 假设一年252个交易日
    const annualizedReturn = years > 0 ? Math.pow(finalEquity / initialCapital, 1 / years) - 1 : 0;
    
    // 计算每日收益率
    const dailyReturns: number[] = [];
    for (let i = 1; i < equityCurve.length; i++) {
      const returnRate = (equityCurve[i] - equityCurve[i - 1]) / equityCurve[i - 1];
      dailyReturns.push(returnRate);
    }
    
    // 计算波动率（标准差）
    const avgReturn = dailyReturns.reduce((a, b) => a + b, 0) / dailyReturns.length;
    const variance = dailyReturns.reduce((sum, r) => sum + Math.pow(r - avgReturn, 2), 0) / dailyReturns.length;
    const volatility = Math.sqrt(variance) * Math.sqrt(252) * 100; // 年化波动率
    
    // 计算夏普比率（假设无风险利率为3%）
    const riskFreeRate = 0.03;
    const sharpeRatio = volatility > 0 ? ((annualizedReturn * 100 - riskFreeRate) / volatility) : 0;
    
    // 计算最大回撤
    let maxDrawdown = 0;
    let maxDrawdownRate = 0;
    let peak = equityCurve[0];
    
    for (let i = 1; i < equityCurve.length; i++) {
      if (equityCurve[i] > peak) {
        peak = equityCurve[i];
      }
      const drawdown = peak - equityCurve[i];
      const drawdownRate = (drawdown / peak) * 100;
      
      if (drawdown > maxDrawdown) {
        maxDrawdown = drawdown;
        maxDrawdownRate = drawdownRate;
      }
    }
    
    // 计算胜率
    const profitDays = dailyReturns.filter(r => r > 0).length;
    const winRate = dailyReturns.length > 0 ? (profitDays / dailyReturns.length) * 100 : 0;
    
    // 计算盈亏比
    const avgProfit = dailyReturns.filter(r => r > 0).reduce((a, b) => a + b, 0) / Math.max(profitDays, 1);
    const avgLoss = Math.abs(dailyReturns.filter(r => r < 0).reduce((a, b) => a + b, 0) / Math.max(dailyReturns.length - profitDays, 1));
    const profitLossRatio = avgLoss > 0 ? avgProfit / avgLoss : 0;
    
    // Alpha 和 Beta（简化计算，实际需要对比基准收益）
    const alpha = annualizedReturn * 100 - 8; // 假设市场收益率8%
    const beta = 1.0; // 简化为1，实际需要与基准对比计算
    
    // 超额收益（相对于基准）
    const benchmarkReturn = 8; // 假设基准收益率8%
    const excessReturn = (annualizedReturn * 100 - benchmarkReturn) * initialCapital / 100;
    const excessReturnRate = annualizedReturn * 100 - benchmarkReturn;
    
    return {
      totalReturn,
      totalReturnRate,
      annualizedReturn: annualizedReturn * 100,
      volatility,
      sharpeRatio,
      maxDrawdown,
      maxDrawdownRate,
      winRate,
      profitLossRatio,
      alpha,
      beta,
      excessReturn,
      excessReturnRate,
    };
  };

  const metrics = calculateMetrics();
  const hasData = profitData && profitData.length > 0;

  // 格式化数字显示
  const formatNumber = (num: number, precision: number = 2) => {
    return isNaN(num) || !isFinite(num) ? '0.00' : num.toFixed(precision);
  };

  const formatPercent = (num: number, precision: number = 2) => {
    return isNaN(num) || !isFinite(num) ? '0.00%' : num.toFixed(precision) + '%';
  };

  const formatMoney = (num: number) => {
    return isNaN(num) || !isFinite(num) ? '¥0.00' : '¥' + num.toFixed(2);
  };

  // 小型指标卡片组件
  const MetricCard: React.FC<{
    title: string;
    value: string | number;
    suffix?: string;
    color?: string;
    icon?: React.ReactNode;
    extra?: React.ReactNode;
  }> = ({ title, value, suffix, color, icon, extra }) => (
    <div
      style={{
        background: '#fff',
        border: '1px solid #f0f0f0',
        borderRadius: '6px',
        padding: '10px 12px',
        height: '100%',
        transition: 'all 0.3s',
        cursor: 'default',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.boxShadow = '0 2px 8px rgba(0,0,0,0.08)';
        e.currentTarget.style.borderColor = '#d9d9d9';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.boxShadow = 'none';
        e.currentTarget.style.borderColor = '#f0f0f0';
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <Text type="secondary" style={{ fontSize: 12, lineHeight: '16px' }}>
          {icon && <span style={{ marginRight: 4 }}>{icon}</span>}
          {title}
        </Text>
        {extra}
      </div>
      <div
        style={{
          fontSize: 18,
          fontWeight: 600,
          color: color || '#262626',
          marginTop: 6,
          lineHeight: '24px',
        }}
      >
        {value}
        {suffix && <span style={{ fontSize: 14, marginLeft: 2 }}>{suffix}</span>}
      </div>
    </div>
  );

  return (
    <div style={{ padding: '16px 20px' }}>
      {/* 页面标题 */}
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Space>
          <LineChartOutlined style={{ fontSize: 20, color: '#1890ff' }} />
          <Title level={4} style={{ margin: 0 }}>收益概述</Title>
          <Tag color={hasData ? 'blue' : 'default'}>{profitData.length} 交易日</Tag>
        </Space>
        <Space size={4}>
          <Tag color={metrics.totalReturnRate >= 0 ? 'success' : 'error'} style={{ margin: 0 }}>
            总收益率 {metrics.totalReturnRate >= 0 ? '+' : ''}{formatPercent(metrics.totalReturnRate)}
          </Tag>
          <Tag color={metrics.sharpeRatio >= 1 ? 'success' : 'warning'} style={{ margin: 0 }}>
            夏普 {formatNumber(metrics.sharpeRatio)}
          </Tag>
        </Space>
      </div>

      {/* 无数据提示 */}
      {!hasData && (
        <Alert
          message="暂无回测数据"
          description="当前尚未加载回测数据，以下显示的是默认指标值（0）。请等待回测运行或刷新数据后查看真实的绩效指标。"
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}

      <Row gutter={[12, 12]}>
        {/* 核心收益指标 - 左侧大卡片 */}
        <Col span={12}>
          <Card
            title={
              <Space>
                <TrophyOutlined style={{ color: '#faad14' }} />
                <span style={{ fontSize: 14, fontWeight: 500 }}>核心收益指标</span>
              </Space>
            }
            size="small"
            bodyStyle={{ padding: '12px' }}
            headStyle={{ minHeight: 40, padding: '0 12px' }}
          >
            <Row gutter={[8, 8]}>
              <Col span={12}>
                <MetricCard
                  title="策略收益"
                  value={formatMoney(metrics.totalReturn)}
                  color={metrics.totalReturn >= 0 ? '#52c41a' : '#ff4d4f'}
                  icon={metrics.totalReturn >= 0 ? <RiseOutlined /> : <FallOutlined />}
                  extra={
                    <Tag
                      color={metrics.totalReturnRate >= 0 ? 'success' : 'error'}
                      style={{ fontSize: 11, padding: '0 4px', lineHeight: '18px' }}
                    >
                      {metrics.totalReturnRate >= 0 ? '+' : ''}{metrics.totalReturnRate.toFixed(2)}%
                    </Tag>
                  }
                />
              </Col>
              <Col span={12}>
                <MetricCard
                  title="年化收益率"
                  value={metrics.annualizedReturn.toFixed(2)}
                  suffix="%"
                  color={metrics.annualizedReturn >= 0 ? '#52c41a' : '#ff4d4f'}
                />
              </Col>
              <Col span={12}>
                <MetricCard
                  title="超额收益"
                  value={formatMoney(metrics.excessReturn)}
                  color={metrics.excessReturn >= 0 ? '#52c41a' : '#ff4d4f'}
                  extra={
                    <Text type="secondary" style={{ fontSize: 11 }}>
                      vs 基准
                    </Text>
                  }
                />
              </Col>
              <Col span={12}>
                <MetricCard
                  title="超额年化"
                  value={metrics.excessReturnRate.toFixed(2)}
                  suffix="%"
                  color={metrics.excessReturnRate >= 0 ? '#52c41a' : '#ff4d4f'}
                />
              </Col>
              <Col span={12}>
                <MetricCard
                  title="日均收益"
                  value={formatMoney(metrics.totalReturn / Math.max(profitData.length, 1))}
                  color={metrics.totalReturn >= 0 ? '#52c41a' : '#ff4d4f'}
                />
              </Col>
              <Col span={12}>
                <MetricCard
                  title="日均超额收益"
                  value={formatMoney(metrics.excessReturn / Math.max(profitData.length, 1))}
                  color={metrics.excessReturn >= 0 ? '#52c41a' : '#ff4d4f'}
                />
              </Col>
            </Row>
          </Card>
        </Col>

        {/* 风险控制指标 - 右上卡片 */}
        <Col span={12}>
          <Card
            title={
              <Space>
                <SafetyOutlined style={{ color: '#ff4d4f' }} />
                <span style={{ fontSize: 14, fontWeight: 500 }}>风险控制指标</span>
              </Space>
            }
            size="small"
            bodyStyle={{ padding: '12px' }}
            headStyle={{ minHeight: 40, padding: '0 12px' }}
          >
            <Row gutter={[8, 8]}>
              <Col span={12}>
                <MetricCard
                  title="最大回撤"
                  value={metrics.maxDrawdownRate.toFixed(2)}
                  suffix="%"
                  color="#ff4d4f"
                  extra={
                    <Progress
                      type="circle"
                      percent={Math.min(metrics.maxDrawdownRate, 100)}
                      width={24}
                      strokeColor="#ff4d4f"
                      format={() => ''}
                    />
                  }
                />
              </Col>
              <Col span={12}>
                <MetricCard
                  title="回撤金额"
                  value={formatMoney(metrics.maxDrawdown)}
                  color="#ff4d4f"
                />
              </Col>
              <Col span={12}>
                <MetricCard
                  title="夏普比率"
                  value={metrics.sharpeRatio.toFixed(3)}
                  color={metrics.sharpeRatio >= 1 ? '#52c41a' : metrics.sharpeRatio >= 0.5 ? '#faad14' : '#ff4d4f'}
                  extra={
                    <Tag color={metrics.sharpeRatio >= 1 ? 'success' : 'warning'} style={{ fontSize: 10, padding: '0 3px' }}>
                      {metrics.sharpeRatio >= 2 ? '优秀' : metrics.sharpeRatio >= 1 ? '良好' : '一般'}
                    </Tag>
                  }
                />
              </Col>
              <Col span={12}>
                <MetricCard
                  title="策略波动率"
                  value={metrics.volatility.toFixed(2)}
                  suffix="%"
                  color="#1890ff"
                />
              </Col>
              <Col span={12}>
                <MetricCard title="阿尔法 α" value={metrics.alpha.toFixed(2)} suffix="%" color={metrics.alpha >= 0 ? '#52c41a' : '#ff4d4f'} />
              </Col>
              <Col span={12}>
                <MetricCard title="贝塔 β" value={metrics.beta.toFixed(3)} color="#722ed1" />
              </Col>
            </Row>
          </Card>
        </Col>

        {/* 交易统计指标 */}
        <Col span={12}>
          <Card
            title={
              <Space>
                <ThunderboltOutlined style={{ color: '#13c2c2' }} />
                <span style={{ fontSize: 14, fontWeight: 500 }}>交易统计</span>
              </Space>
            }
            size="small"
            bodyStyle={{ padding: '12px' }}
            headStyle={{ minHeight: 40, padding: '0 12px' }}
          >
            <Row gutter={[8, 8]}>
              <Col span={8}>
                <MetricCard
                  title="总交易日"
                  value={profitData.length}
                  suffix="天"
                  color="#1890ff"
                />
              </Col>
              <Col span={8}>
                <MetricCard
                  title="盈利日数"
                  value={Math.round(profitData.length * metrics.winRate / 100)}
                  suffix="天"
                  color="#52c41a"
                />
              </Col>
              <Col span={8}>
                <MetricCard
                  title="亏损日数"
                  value={profitData.length - Math.round(profitData.length * metrics.winRate / 100)}
                  suffix="天"
                  color="#ff4d4f"
                />
              </Col>
              <Col span={12}>
                <div
                  style={{
                    background: '#fff',
                    border: '1px solid #f0f0f0',
                    borderRadius: '6px',
                    padding: '10px 12px',
                  }}
                >
                  <Text type="secondary" style={{ fontSize: 12 }}>胜率</Text>
                  <div style={{ marginTop: 6 }}>
                    <Progress
                      percent={metrics.winRate}
                      strokeColor={{
                        '0%': '#ff4d4f',
                        '50%': '#faad14',
                        '100%': '#52c41a',
                      }}
                      format={(percent) => (
                        <span style={{ fontSize: 14, fontWeight: 600, color: '#262626' }}>
                          {percent?.toFixed(1)}%
                        </span>
                      )}
                    />
                  </div>
                </div>
              </Col>
              <Col span={12}>
                <MetricCard
                  title="盈亏比"
                  value={metrics.profitLossRatio.toFixed(2)}
                  color={metrics.profitLossRatio >= 1 ? '#52c41a' : '#faad14'}
                  extra={
                    <Tag color={metrics.profitLossRatio >= 2 ? 'success' : metrics.profitLossRatio >= 1 ? 'warning' : 'error'} style={{ fontSize: 10, padding: '0 3px' }}>
                      {metrics.profitLossRatio >= 2 ? '优秀' : metrics.profitLossRatio >= 1 ? '良好' : '偏低'}
                    </Tag>
                  }
                />
              </Col>
            </Row>
          </Card>
        </Col>

        {/* 时间统计 */}
        <Col span={12}>
          <Card
            title={
              <Space>
                <LineChartOutlined style={{ color: '#722ed1' }} />
                <span style={{ fontSize: 14, fontWeight: 500 }}>时间与收益</span>
              </Space>
            }
            size="small"
            bodyStyle={{ padding: '12px' }}
            headStyle={{ minHeight: 40, padding: '0 12px' }}
          >
            <Row gutter={[8, 8]}>
              <Col span={12}>
                <MetricCard
                  title="开始日期"
                  value={String(config.start_date || 'N/A').replace(/(\d{4})(\d{2})(\d{2})/, '$1-$2-$3')}
                  color="#722ed1"
                />
              </Col>
              <Col span={12}>
                <MetricCard
                  title="结束日期"
                  value={String(config.end_date || 'N/A').replace(/(\d{4})(\d{2})(\d{2})/, '$1-$2-$3')}
                  color="#722ed1"
                />
              </Col>
              <Col span={12}>
                <MetricCard
                  title="初始资金"
                  value={(config.start_capital * 10000).toLocaleString('zh-CN')}
                  suffix="元"
                  color="#1890ff"
                />
              </Col>
              <Col span={12}>
                <MetricCard
                  title="最终资金"
                  value={(config.start_capital * 10000 + metrics.totalReturn).toLocaleString('zh-CN')}
                  suffix="元"
                  color={metrics.totalReturn >= 0 ? '#52c41a' : '#ff4d4f'}
                />
              </Col>
            </Row>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default PerformanceMetrics;

