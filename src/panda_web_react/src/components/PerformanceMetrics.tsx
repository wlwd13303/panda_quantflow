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
  finalEquity: number;
  initialCapital: number;
  
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
        finalEquity: 0,
        initialCapital: 0,
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

    // 转换为元，如果配置中没有初始资金，则从数据中推断
    let initialCapital = (config.start_capital || 0) * 10000;
    
    // 获取资产净值序列
    const equityCurve = profitData.map((item, index) => {
      let value = Number(item.total_value ?? item.total_profit ?? item.strategy_profit);
      
      // 如果初始资金为0，从第一个有效数据点推断初始资金
      if (initialCapital === 0 && index === 0 && value > 0 && isFinite(value)) {
        initialCapital = value;
      }
      
      // 如果值为0、负数或无效，使用初始资金
      if (!value || value <= 0 || !isFinite(value)) {
        value = initialCapital > 0 ? initialCapital : 1000000; // 默认100万
      }
      
      // 特别处理第一个数据点：如果第一个点的值异常小（小于初始资金的50%），则认为是数据错误，使用初始资金
      if (index === 0 && initialCapital > 0 && value < initialCapital * 0.5) {
        value = initialCapital;
      }
      
      return value;
    });
    
    const finalEquity = equityCurve[equityCurve.length - 1] || initialCapital;
    const totalReturn = finalEquity - initialCapital;
    
    // 计算收益率，避免除以0
    let totalReturnRate = 0;
    if (initialCapital > 0 && isFinite(initialCapital) && isFinite(totalReturn)) {
      totalReturnRate = (totalReturn / initialCapital) * 100;
      if (!isFinite(totalReturnRate)) totalReturnRate = 0;
    }
    
    // 计算年化收益率，避免除以0
    const tradingDays = profitData.length;
    const years = tradingDays / 252; // 假设一年252个交易日
    let annualizedReturn = 0;
    if (years > 0 && initialCapital > 0 && finalEquity > 0 && isFinite(finalEquity) && isFinite(initialCapital)) {
      const ratio = finalEquity / initialCapital;
      if (ratio > 0 && isFinite(ratio)) {
        annualizedReturn = Math.pow(ratio, 1 / years) - 1;
        if (!isFinite(annualizedReturn)) annualizedReturn = 0;
      }
    }
    
    // 计算每日收益率
    const dailyReturns: number[] = [];
    for (let i = 1; i < equityCurve.length; i++) {
      const prevValue = equityCurve[i - 1];
      const currValue = equityCurve[i];
      if (prevValue > 0 && isFinite(prevValue) && isFinite(currValue)) {
        const returnRate = (currValue - prevValue) / prevValue;
        if (isFinite(returnRate)) {
          dailyReturns.push(returnRate);
        }
      }
    }
    
    // 计算波动率（标准差）
    let volatility = 0;
    if (dailyReturns.length > 0) {
      const avgReturn = dailyReturns.reduce((a, b) => a + b, 0) / dailyReturns.length;
      if (isFinite(avgReturn)) {
        const variance = dailyReturns.reduce((sum, r) => {
          const diff = r - avgReturn;
          return sum + (diff * diff);
        }, 0) / dailyReturns.length;
        if (isFinite(variance) && variance >= 0) {
          volatility = Math.sqrt(variance) * Math.sqrt(252) * 100; // 年化波动率
          if (!isFinite(volatility)) volatility = 0;
        }
      }
    }
    
    // 计算夏普比率（假设无风险利率为3%）
    // 注意：annualizedReturn 是小数形式（如 0.08 表示 8%），volatility 是百分比形式（如 10.6 表示 10.6%）
    const riskFreeRate = 0.03; // 无风险利率（小数形式，3%）
    let sharpeRatio = 0;
    if (volatility > 0 && isFinite(annualizedReturn) && isFinite(volatility)) {
      // 统一单位：将年化收益率转换为百分比，无风险利率也转换为百分比
      // Sharpe Ratio = (Rp - Rf) / σp，其中 Rp 和 Rf 是百分比，σp 也是百分比
      sharpeRatio = ((annualizedReturn * 100 - riskFreeRate * 100) / volatility);
      if (!isFinite(sharpeRatio)) sharpeRatio = 0;
    }
    
    // 计算最大回撤
    let maxDrawdown = 0;
    let maxDrawdownRate = 0;
    if (equityCurve.length > 0) {
      let peak = equityCurve[0];
      if (peak > 0 && isFinite(peak)) {
        for (let i = 1; i < equityCurve.length; i++) {
          const value = equityCurve[i];
          if (isFinite(value)) {
            if (value > peak) {
              peak = value;
            }
            if (peak > 0) {
              const drawdown = peak - value;
              const drawdownRate = (drawdown / peak) * 100;
              
              if (isFinite(drawdown) && isFinite(drawdownRate) && drawdown > maxDrawdown) {
                maxDrawdown = drawdown;
                maxDrawdownRate = drawdownRate;
              }
            }
          }
        }
      }
    }
    
    // 计算胜率
    const profitDays = dailyReturns.filter(r => r > 0).length;
    const winRate = dailyReturns.length > 0 ? (profitDays / dailyReturns.length) * 100 : 0;
    
    // 计算盈亏比
    let profitLossRatio = 0;
    if (dailyReturns.length > 0) {
      const profitReturns = dailyReturns.filter(r => r > 0);
      const lossReturns = dailyReturns.filter(r => r < 0);
      
      if (profitReturns.length > 0 && lossReturns.length > 0) {
        const avgProfit = profitReturns.reduce((a, b) => a + b, 0) / profitReturns.length;
        const avgLoss = Math.abs(lossReturns.reduce((a, b) => a + b, 0) / lossReturns.length);
        
        if (avgLoss > 0 && isFinite(avgProfit) && isFinite(avgLoss)) {
          profitLossRatio = avgProfit / avgLoss;
          if (!isFinite(profitLossRatio)) profitLossRatio = 0;
        }
      }
    }
    
    // Alpha 和 Beta（简化计算，实际需要对比基准收益）
    let alpha = 0;
    if (isFinite(annualizedReturn)) {
      alpha = annualizedReturn * 100 - 8; // 假设市场收益率8%
      if (!isFinite(alpha)) alpha = 0;
    }
    const beta = 1.0; // 简化为1，实际需要与基准对比计算
    
    // 超额收益（相对于基准）
    // 计算基准总收益（假设年化8%的收益率）
    const benchmarkAnnualRate = 0.08; // 基准年化收益率8%
    let benchmarkTotalReturn = 0;
    let excessReturn = 0;
    let excessReturnRate = 0;
    
    if (years > 0 && initialCapital > 0 && isFinite(years) && isFinite(initialCapital)) {
      // 基准的总收益 = 初始资金 * (1 + 年化率)^年数 - 初始资金
      const benchmarkFinalValue = initialCapital * Math.pow(1 + benchmarkAnnualRate, years);
      if (isFinite(benchmarkFinalValue)) {
        benchmarkTotalReturn = benchmarkFinalValue - initialCapital;
        if (isFinite(benchmarkTotalReturn)) {
          // 超额收益（金额）= 实际收益 - 基准收益
          excessReturn = totalReturn - benchmarkTotalReturn;
          if (!isFinite(excessReturn)) excessReturn = 0;
          
          // 超额收益率 = 超额收益 / 初始资金 * 100
          excessReturnRate = (excessReturn / initialCapital) * 100;
          if (!isFinite(excessReturnRate)) excessReturnRate = 0;
        }
      }
    }
    
    return {
      totalReturn,
      totalReturnRate,
      annualizedReturn: isFinite(annualizedReturn) ? annualizedReturn * 100 : 0,
      volatility: isFinite(volatility) ? volatility : 0,
      sharpeRatio: isFinite(sharpeRatio) ? sharpeRatio : 0,
      maxDrawdown: isFinite(maxDrawdown) ? maxDrawdown : 0,
      maxDrawdownRate: isFinite(maxDrawdownRate) ? maxDrawdownRate : 0,
      winRate: isFinite(winRate) ? winRate : 0,
      profitLossRatio: isFinite(profitLossRatio) ? profitLossRatio : 0,
      alpha: isFinite(alpha) ? alpha : 0,
      beta: isFinite(beta) ? beta : 0,
      excessReturn: isFinite(excessReturn) ? excessReturn : 0,
      excessReturnRate: isFinite(excessReturnRate) ? excessReturnRate : 0,
      finalEquity: isFinite(finalEquity) ? finalEquity : 0, // 添加总资产字段
      initialCapital: isFinite(initialCapital) ? initialCapital : 0, // 添加初始资金字段（可能从数据推断）
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
          <Tag color={metrics.totalReturnRate >= 0 ? 'error' : 'success'} style={{ margin: 0 }}>
            总收益率 {metrics.totalReturnRate >= 0 ? '+' : ''}{formatPercent(metrics.totalReturnRate)}
          </Tag>
          <Tag color={metrics.sharpeRatio >= 1 ? 'success' : metrics.sharpeRatio >= 0.5 ? 'warning' : 'error'} style={{ margin: 0 }}>
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
            styles={{ body: { padding: '12px' } }}
            headStyle={{ minHeight: 40, padding: '0 12px' }}
          >
            <Row gutter={[8, 8]}>
              <Col span={12}>
                <MetricCard
                  title="策略收益"
                  value={formatMoney(metrics.totalReturn)}
                  color={metrics.totalReturn >= 0 ? '#ff4d4f' : '#52c41a'}
                  icon={metrics.totalReturn >= 0 ? <RiseOutlined /> : <FallOutlined />}
                  extra={
                    <Tag
                      color={metrics.totalReturnRate >= 0 ? 'error' : 'success'}
                      style={{ fontSize: 11, padding: '0 4px', lineHeight: '18px' }}
                    >
                      {metrics.totalReturnRate >= 0 ? '+' : ''}{formatPercent(metrics.totalReturnRate)}
                    </Tag>
                  }
                />
              </Col>
              <Col span={12}>
                <MetricCard
                  title="年化收益率"
                  value={formatPercent(metrics.annualizedReturn)}
                  color={metrics.annualizedReturn >= 0 ? '#ff4d4f' : '#52c41a'}
                />
              </Col>
              <Col span={12}>
                <MetricCard
                  title="超额收益"
                  value={formatMoney(metrics.excessReturn)}
                  color={metrics.excessReturn >= 0 ? '#ff4d4f' : '#52c41a'}
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
                  value={formatPercent(metrics.excessReturnRate)}
                  color={metrics.excessReturnRate >= 0 ? '#ff4d4f' : '#52c41a'}
                />
              </Col>
              <Col span={12}>
                <MetricCard
                  title="日均收益"
                  value={formatMoney(metrics.totalReturn / Math.max(profitData.length, 1))}
                  color={metrics.totalReturn >= 0 ? '#ff4d4f' : '#52c41a'}
                />
              </Col>
              <Col span={12}>
                <MetricCard
                  title="日均超额收益"
                  value={formatMoney(metrics.excessReturn / Math.max(profitData.length, 1))}
                  color={metrics.excessReturn >= 0 ? '#ff4d4f' : '#52c41a'}
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
            styles={{ body: { padding: '12px' } }}
            headStyle={{ minHeight: 40, padding: '0 12px' }}
          >
            <Row gutter={[8, 8]}>
              <Col span={12}>
                <MetricCard
                  title="最大回撤"
                  value={formatPercent(metrics.maxDrawdownRate)}
                  color="#ff4d4f"
                  extra={
                    <Progress
                      type="circle"
                      percent={Math.min(metrics.maxDrawdownRate, 100)}
                      size={24}
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
                    <Tag color={metrics.sharpeRatio >= 2 ? 'success' : metrics.sharpeRatio >= 1 ? 'success' : metrics.sharpeRatio >= 0.5 ? 'warning' : 'error'} style={{ fontSize: 10, padding: '0 3px' }}>
                      {metrics.sharpeRatio >= 2 ? '优秀' : metrics.sharpeRatio >= 1 ? '良好' : '一般'}
                    </Tag>
                  }
                />
              </Col>
              <Col span={12}>
                <MetricCard
                  title="策略波动率"
                  value={formatPercent(metrics.volatility)}
                  color="#1890ff"
                />
              </Col>
              <Col span={12}>
                <MetricCard title="阿尔法 α" value={formatPercent(metrics.alpha)} color={metrics.alpha >= 0 ? '#52c41a' : '#ff4d4f'} />
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
            styles={{ body: { padding: '12px' } }}
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
                  color="#ff4d4f"
                />
              </Col>
              <Col span={8}>
                <MetricCard
                  title="亏损日数"
                  value={profitData.length - Math.round(profitData.length * metrics.winRate / 100)}
                  suffix="天"
                  color="#52c41a"
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
                        '0%': '#52c41a',
                        '50%': '#faad14',
                        '100%': '#ff4d4f',
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
                  value={formatNumber(metrics.profitLossRatio, 2)}
                  color={metrics.profitLossRatio >= 2 ? '#52c41a' : metrics.profitLossRatio >= 1 ? '#faad14' : '#ff4d4f'}
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
            styles={{ body: { padding: '12px' } }}
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
                  value={formatMoney(metrics.initialCapital)}
                  color="#1890ff"
                />
              </Col>
              <Col span={12}>
                <MetricCard
                  title="最终资金"
                  value={formatMoney(metrics.finalEquity)}
                  color={metrics.totalReturn >= 0 ? '#ff4d4f' : '#52c41a'}
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

