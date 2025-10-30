import React, { useState } from 'react';
import { Card, DatePicker, Space, Checkbox, Row, Col } from 'antd';
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

    // 策略收益曲线（归一化为百分比）
    const strategyEquity = filteredData.map(item => {
      const value = Number(item.total_value ?? item.total_profit ?? item.strategy_profit ?? initialCapital);
      return ((value - initialCapital) / initialCapital * 100).toFixed(2);
    });

    // 基准收益曲线（模拟，假设年化8%的线性增长）
    const benchmarkEquity = filteredData.map((_, index) => {
      const days = index;
      const dailyReturn = 0.08 / 252; // 年化8%转换为日收益
      return (dailyReturn * days * 100).toFixed(2);
    });

    // 超额收益曲线
    const excessEquity = strategyEquity.map((val, idx) => 
      (parseFloat(val) - parseFloat(benchmarkEquity[idx])).toFixed(2)
    );

    const series: any[] = [];
    const legendData: string[] = [];

    if (showStrategy) {
      series.push({
        name: '策略收益',
        type: 'line',
        data: strategyEquity,
        smooth: true,
        lineStyle: { color: '#5470c6', width: 2 },
        showSymbol: false,
      });
      legendData.push('策略收益');
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

    if (showBenchmark) {
      series.push({
        name: '中小涨指',
        type: 'line',
        data: benchmarkEquity,
        smooth: true,
        lineStyle: { color: '#fac858', width: 2, type: 'dashed' },
        showSymbol: false,
      });
      legendData.push('中小涨指');
    }

    return {
      title: {
        text: '收益曲线',
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
            content += `${param.marker} ${param.seriesName}: ${value >= 0 ? '+' : ''}${value.toFixed(2)}%<br/>`;
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
        name: '收益率(%)',
        axisLabel: {
          formatter: '{value}%'
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

  return (
    <Card>
      <div style={{ marginBottom: 16 }}>
        <Row justify="space-between" align="middle">
          <Col>
            <Space>
              <span style={{ fontSize: 12, color: '#666' }}>缩略：</span>
              <Checkbox checked={showStrategy} onChange={(e) => setShowStrategy(e.target.checked)}>
                <span style={{ fontSize: 12 }}>策略收益</span>
              </Checkbox>
              <Checkbox checked={showExcess} onChange={(e) => setShowExcess(e.target.checked)}>
                <span style={{ fontSize: 12 }}>超额收益</span>
              </Checkbox>
              <Checkbox checked={showBenchmark} onChange={(e) => setShowBenchmark(e.target.checked)}>
                <span style={{ fontSize: 12 }}>中小涨指</span>
              </Checkbox>
            </Space>
          </Col>
          <Col>
            <Space>
              <span style={{ fontSize: 12, color: '#666' }}>时间：</span>
              <RangePicker
                size="small"
                value={dateRange}
                onChange={(dates) => setDateRange(dates as [dayjs.Dayjs, dayjs.Dayjs] | null)}
                format="YYYY-MM-DD"
                allowClear
              />
            </Space>
          </Col>
        </Row>
      </div>
      <ReactECharts option={getChartOption()} style={{ height: 450 }} />
    </Card>
  );
};

export default EnhancedProfitChart;

