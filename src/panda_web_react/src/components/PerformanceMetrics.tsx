import React from 'react';
import { Card, Row, Col, Statistic, Divider, Typography } from 'antd';
import { ArrowUpOutlined, ArrowDownOutlined } from '@ant-design/icons';
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

  return (
    <div style={{ padding: '20px' }}>
      {/* 收益概述 */}
      <Card>
        <Title level={4}>收益概述</Title>
        <Row gutter={[24, 24]} style={{ marginTop: 20 }}>
          <Col span={6}>
            <Statistic
              title="策略收益"
              value={metrics.totalReturn}
              precision={2}
              prefix="¥"
              valueStyle={{ color: metrics.totalReturn >= 0 ? '#3f8600' : '#cf1322' }}
              suffix={
                metrics.totalReturn >= 0 ? (
                  <ArrowUpOutlined />
                ) : (
                  <ArrowDownOutlined />
                )
              }
            />
            <Text type="secondary" style={{ fontSize: 12 }}>
              ({formatPercent(metrics.totalReturnRate)})
            </Text>
          </Col>
          
          <Col span={6}>
            <Statistic
              title="超额收益"
              value={metrics.excessReturn}
              precision={2}
              prefix="¥"
              valueStyle={{ color: metrics.excessReturn >= 0 ? '#3f8600' : '#cf1322' }}
            />
            <Text type="secondary" style={{ fontSize: 12 }}>
              ({formatPercent(metrics.excessReturnRate)})
            </Text>
          </Col>
          
          <Col span={6}>
            <Statistic
              title="年化收益率"
              value={formatPercent(metrics.annualizedReturn)}
              valueStyle={{ color: metrics.annualizedReturn >= 0 ? '#3f8600' : '#cf1322' }}
            />
          </Col>
          
          <Col span={6}>
            <Statistic
              title="夏普比率"
              value={formatNumber(metrics.sharpeRatio)}
              valueStyle={{ color: metrics.sharpeRatio >= 1 ? '#3f8600' : '#cf1322' }}
            />
          </Col>
        </Row>

        <Divider />

        <Row gutter={[24, 24]}>
          <Col span={6}>
            <div style={{ marginBottom: 16 }}>
              <Text type="secondary">盈亏比率</Text>
              <div style={{ fontSize: 20, fontWeight: 500 }}>
                {formatNumber(metrics.profitLossRatio)}
              </div>
            </div>
          </Col>
          
          <Col span={6}>
            <div style={{ marginBottom: 16 }}>
              <Text type="secondary">阿尔法</Text>
              <div style={{ fontSize: 20, fontWeight: 500, color: metrics.alpha >= 0 ? '#3f8600' : '#cf1322' }}>
                {formatPercent(metrics.alpha)}
              </div>
            </div>
          </Col>
          
          <Col span={6}>
            <div style={{ marginBottom: 16 }}>
              <Text type="secondary">贝塔</Text>
              <div style={{ fontSize: 20, fontWeight: 500 }}>
                {formatNumber(metrics.beta)}
              </div>
            </div>
          </Col>
          
          <Col span={6}>
            <div style={{ marginBottom: 16 }}>
              <Text type="secondary">胜率</Text>
              <div style={{ fontSize: 20, fontWeight: 500 }}>
                {formatPercent(metrics.winRate)}
              </div>
            </div>
          </Col>
        </Row>

        <Divider />

        <Row gutter={[24, 24]}>
          <Col span={6}>
            <div style={{ marginBottom: 16 }}>
              <Text type="secondary">日均超额收益</Text>
              <div style={{ fontSize: 18, fontWeight: 500 }}>
                {formatMoney(metrics.excessReturn / Math.max(profitData.length, 1))}
              </div>
            </div>
          </Col>
          
          <Col span={6}>
            <div style={{ marginBottom: 16 }}>
              <Text type="secondary">超额收益率年化</Text>
              <div style={{ fontSize: 18, fontWeight: 500 }}>
                {formatPercent(metrics.excessReturnRate)}
              </div>
            </div>
          </Col>
          
          <Col span={6}>
            <div style={{ marginBottom: 16 }}>
              <Text type="secondary">策略波动率</Text>
              <div style={{ fontSize: 18, fontWeight: 500 }}>
                {formatPercent(metrics.volatility)}
              </div>
            </div>
          </Col>
          
          <Col span={6}>
            <div style={{ marginBottom: 16 }}>
              <Text type="secondary">最大回撤</Text>
              <div style={{ fontSize: 18, fontWeight: 500, color: '#cf1322' }}>
                {formatPercent(metrics.maxDrawdownRate)}
              </div>
            </div>
          </Col>
        </Row>

        <Divider />

        <Row gutter={[24, 24]}>
          <Col span={8}>
            <div style={{ marginBottom: 16 }}>
              <Text type="secondary">日数</Text>
              <div style={{ fontSize: 18, fontWeight: 500 }}>
                {profitData.length}
              </div>
            </div>
          </Col>
          
          <Col span={8}>
            <div style={{ marginBottom: 16 }}>
              <Text type="secondary">盈利日数</Text>
              <div style={{ fontSize: 18, fontWeight: 500, color: '#3f8600' }}>
                {Math.round(profitData.length * metrics.winRate / 100)}
              </div>
            </div>
          </Col>
          
          <Col span={8}>
            <div style={{ marginBottom: 16 }}>
              <Text type="secondary">亏损日数</Text>
              <div style={{ fontSize: 18, fontWeight: 500, color: '#cf1322' }}>
                {profitData.length - Math.round(profitData.length * metrics.winRate / 100)}
              </div>
            </div>
          </Col>
        </Row>
      </Card>
    </div>
  );
};

export default PerformanceMetrics;

