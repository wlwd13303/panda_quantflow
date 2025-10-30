import React, { useState } from 'react';
import { Card, DatePicker, Space, Checkbox, Row, Col, Empty } from 'antd';
import ReactECharts from 'echarts-for-react';
import type { ProfitData } from '@/types';
import dayjs from 'dayjs';

const { RangePicker } = DatePicker;

interface EnhancedProfitChartProps {
  profitData: ProfitData[];
  config: {
    start_capital: number;
    start_date: string;
    end_date: string;
  };
}

const EnhancedProfitChart: React.FC<EnhancedProfitChartProps> = ({ profitData, config }) => {
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs, dayjs.Dayjs] | null>(null);
  const [showStrategy, setShowStrategy] = useState(true);
  const [showExcess, setShowExcess] = useState(true);
  const [showBenchmark, setShowBenchmark] = useState(true);

  // 过滤数据根据日期范围
  const getFilteredData = () => {
    if (!dateRange) return profitData;
    
    const [start, end] = dateRange;
    return profitData.filter(item => {
      const dateStr = String(item.date || item.gmt_create_time || item.gmt_create || '').substring(0, 8);
      const itemDate = dayjs(dateStr, 'YYYYMMDD');
      return itemDate.isAfter(start.subtract(1, 'day')) && itemDate.isBefore(end.add(1, 'day'));
    });
  };

  const filteredData = getFilteredData();

  const getChartOption = () => {
    if (filteredData.length === 0) {
      return {
        title: { text: '暂无数据', left: 'center', top: 'center' }
      };
    }

    const initialCapital = config.start_capital * 10000;
    
    // 日期序列
    const dates = filteredData.map(item => {
      const dateStr = String(item.date || item.gmt_create_time || item.gmt_create || '').substring(0, 8);
      return dateStr.replace(/(\d{4})(\d{2})(\d{2})/, '$1-$2-$3');
    });

    // 策略净值曲线（净值 = 当前资产 / 初始资金）
    const strategyEquity = filteredData.map(item => {
      const value = Number(item.total_value ?? item.total_profit ?? item.strategy_profit ?? initialCapital);
      const netValue = value / initialCapital;
      return netValue.toFixed(4);
    });

    // 基准净值曲线（模拟，假设年化8%的线性增长）
    const benchmarkEquity = filteredData.map((_, index) => {
      const days = index;
      const dailyReturn = 0.08 / 252; // 年化8%转换为日收益
      const netValue = 1 + (dailyReturn * days);
      return netValue.toFixed(4);
    });

    // 超额收益曲线（策略净值 - 基准净值）
    const excessEquity = strategyEquity.map((val, idx) => 
      (parseFloat(val) - parseFloat(benchmarkEquity[idx])).toFixed(4)
    );

    const series: any[] = [];
    const legendData: string[] = [];

    if (showStrategy) {
      series.push({
        name: '策略净值',
        type: 'line',
        data: strategyEquity,
        smooth: true,
        lineStyle: { color: '#5470c6', width: 2 },
        showSymbol: false,
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
      });
      legendData.push('策略净值');
    }

    if (showBenchmark) {
      series.push({
        name: '基准净值',
        type: 'line',
        data: benchmarkEquity,
        smooth: true,
        lineStyle: { color: '#fac858', width: 2, type: 'dashed' },
        showSymbol: false,
      });
      legendData.push('基准净值');
    }

    if (showExcess) {
      series.push({
        name: '超额收益',
        type: 'line',
        data: excessEquity,
        smooth: true,
        lineStyle: { color: '#91cc75', width: 2 },
        showSymbol: false,
      });
      legendData.push('超额收益');
    }

    // 计算累计收益率用于副标题
    const latestNetValue = strategyEquity.length > 0 ? parseFloat(strategyEquity[strategyEquity.length - 1]) : 1;
    const totalReturn = ((latestNetValue - 1) * 100).toFixed(2);

    return {
      title: {
        text: '策略净值曲线',
        subtext: `累计收益率: ${totalReturn}%`,
        left: 10,
        textStyle: { fontSize: 14, fontWeight: 'normal' }
      },
      tooltip: {
        trigger: 'axis',
        formatter: (params: any) => {
          if (!params || params.length === 0) return '';
          let content = params[0].name + '<br/>';
          params.forEach((param: any) => {
            const value = parseFloat(param.value);
            // 对于净值和基准净值，直接显示净值，对于超额收益显示百分比
            if (param.seriesName.includes('净值')) {
              const returnRate = (value - 1) * 100;
              const returnRateStr = returnRate.toFixed(2);
              content += `${param.marker} ${param.seriesName}: ${value.toFixed(4)} (${returnRate >= 0 ? '+' : ''}${returnRateStr}%)<br/>`;
            } else {
              const returnRate = value * 100;
              const returnRateStr = returnRate.toFixed(2);
              content += `${param.marker} ${param.seriesName}: ${returnRate >= 0 ? '+' : ''}${returnRateStr}%<br/>`;
            }
          });
          return content;
        },
      },
      legend: {
        data: legendData,
        top: 35,
        left: 10,
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '10%',
        top: '80px',
        containLabel: true,
      },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: dates,
        axisLabel: {
          rotate: 30,
          interval: Math.floor(dates.length / 10),
        },
      },
      yAxis: {
        type: 'value',
        name: '净值',
        scale: true,  // 不从0开始，自动缩放
        axisLabel: {
          formatter: '{value}'
        },
        splitLine: {
          lineStyle: {
            type: 'dashed',
            color: '#e0e0e0'
          }
        }
      },
      series: series,
      dataZoom: [
        {
          type: 'inside',
          start: 0,
          end: 100,
        },
        {
          type: 'slider',
          start: 0,
          end: 100,
          height: 20,
          bottom: 10,
        },
      ],
    };
  };

  // 计算关键指标
  const getMetrics = () => {
    if (filteredData.length === 0) return null;
    
    const initialCapital = config.start_capital * 10000;
    const values = filteredData.map(item => {
      const value = Number(item.total_value ?? item.total_profit ?? item.strategy_profit ?? initialCapital);
      return value;
    });
    
    const latestValue = values[values.length - 1];
    const totalReturn = ((latestValue - initialCapital) / initialCapital) * 100;
    
    // 计算最大回撤
    let maxDrawdown = 0;
    let peak = values[0];
    for (const value of values) {
      if (value > peak) peak = value;
      const drawdown = ((peak - value) / peak) * 100;
      if (drawdown > maxDrawdown) maxDrawdown = drawdown;
    }
    
    // 计算波动率
    const returns = values.slice(1).map((v, i) => (v - values[i]) / values[i]);
    const avgReturn = returns.reduce((a, b) => a + b, 0) / returns.length;
    const variance = returns.reduce((sum, r) => sum + Math.pow(r - avgReturn, 2), 0) / returns.length;
    const volatility = Math.sqrt(variance) * Math.sqrt(252) * 100;
    
    return {
      totalReturn,
      maxDrawdown,
      volatility,
      latestValue,
    };
  };

  const metrics = getMetrics();

  return (
    <Card 
      styles={{ body: { padding: '16px' } }}
      style={{ height: '100%' }}
    >
      {/* 控制栏 */}
      <div style={{ marginBottom: 16, background: '#fafafa', padding: '12px', borderRadius: '4px' }}>
        <Row justify="space-between" align="middle" gutter={[16, 8]}>
          <Col flex="auto">
            <Space size="middle">
              <div>
                <span style={{ fontSize: 12, color: '#666', marginRight: 8 }}>显示曲线：</span>
                <Checkbox checked={showStrategy} onChange={(e) => setShowStrategy(e.target.checked)}>
                  <span style={{ fontSize: 12 }}>策略净值</span>
                </Checkbox>
                <Checkbox checked={showBenchmark} onChange={(e) => setShowBenchmark(e.target.checked)}>
                  <span style={{ fontSize: 12 }}>基准净值</span>
                </Checkbox>
                <Checkbox checked={showExcess} onChange={(e) => setShowExcess(e.target.checked)}>
                  <span style={{ fontSize: 12 }}>超额收益</span>
                </Checkbox>
              </div>
            </Space>
          </Col>
          <Col>
            <Space>
              <span style={{ fontSize: 12, color: '#666' }}>时间筛选：</span>
              <RangePicker
                size="small"
                value={dateRange}
                onChange={(dates) => setDateRange(dates as [dayjs.Dayjs, dayjs.Dayjs] | null)}
                format="YYYY-MM-DD"
                allowClear
                placeholder={['开始日期', '结束日期']}
              />
            </Space>
          </Col>
        </Row>
        
        {/* 关键指标 */}
        {metrics && (
          <Row gutter={16} style={{ marginTop: 12 }}>
            <Col span={6}>
              <div style={{ textAlign: 'center', padding: '8px', background: '#fff', borderRadius: '4px' }}>
                <div style={{ fontSize: 12, color: '#999' }}>累计收益</div>
                <div style={{ 
                  fontSize: 18, 
                  fontWeight: 'bold', 
                  color: metrics.totalReturn >= 0 ? '#52c41a' : '#ff4d4f',
                  marginTop: 4,
                }}>
                  {metrics.totalReturn >= 0 ? '+' : ''}{metrics.totalReturn.toFixed(2)}%
                </div>
              </div>
            </Col>
            <Col span={6}>
              <div style={{ textAlign: 'center', padding: '8px', background: '#fff', borderRadius: '4px' }}>
                <div style={{ fontSize: 12, color: '#999' }}>最大回撤</div>
                <div style={{ fontSize: 18, fontWeight: 'bold', color: '#ff4d4f', marginTop: 4 }}>
                  {metrics.maxDrawdown.toFixed(2)}%
                </div>
              </div>
            </Col>
            <Col span={6}>
              <div style={{ textAlign: 'center', padding: '8px', background: '#fff', borderRadius: '4px' }}>
                <div style={{ fontSize: 12, color: '#999' }}>年化波动率</div>
                <div style={{ fontSize: 18, fontWeight: 'bold', color: '#1890ff', marginTop: 4 }}>
                  {metrics.volatility.toFixed(2)}%
                </div>
              </div>
            </Col>
            <Col span={6}>
              <div style={{ textAlign: 'center', padding: '8px', background: '#fff', borderRadius: '4px' }}>
                <div style={{ fontSize: 12, color: '#999' }}>当前净值</div>
                <div style={{ fontSize: 18, fontWeight: 'bold', color: '#722ed1', marginTop: 4 }}>
                  {(metrics.latestValue / (config.start_capital * 10000)).toFixed(4)}
                </div>
              </div>
            </Col>
          </Row>
        )}
      </div>
      
      {/* 图表 */}
      {filteredData.length > 0 ? (
        <ReactECharts 
          option={getChartOption()} 
          style={{ height: 450 }}
          opts={{ renderer: 'canvas' }}
        />
      ) : (
        <div style={{ height: 450, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Empty 
            description="暂无收益数据，请先运行回测或等待数据加载" 
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          />
        </div>
      )}
    </Card>
  );
};

export default EnhancedProfitChart;

