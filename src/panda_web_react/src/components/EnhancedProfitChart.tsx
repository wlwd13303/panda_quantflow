import React, { useState, useEffect, useMemo } from 'react';
import { Card, DatePicker, Space, Checkbox, Row, Col, Empty, Spin, message } from 'antd';
import ReactECharts from 'echarts-for-react';
import type { ProfitData } from '@/types';
import dayjs from 'dayjs';
import { quotationApi } from '@/services/api';

const { RangePicker } = DatePicker;

interface EnhancedProfitChartProps {
  profitData: ProfitData[];
  config: {
    start_capital: number;
    start_date: string;
    end_date: string;
    standard_symbol?: string; // 基准指数代码
  };
}

const EnhancedProfitChart: React.FC<EnhancedProfitChartProps> = ({ profitData, config }) => {
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs, dayjs.Dayjs] | null>(null);
  const [showStrategy, setShowStrategy] = useState(true);
  const [showExcess, setShowExcess] = useState(true);
  const [showBenchmark, setShowBenchmark] = useState(true);
  const [indexData, setIndexData] = useState<any[]>([]);
  const [loadingIndex, setLoadingIndex] = useState(false);

  // 获取指数数据
  useEffect(() => {
    const fetchIndexData = async () => {
      const standardSymbol = config.standard_symbol || '000001.SH';
      if (!config.start_date || !config.end_date) {
        return;
      }

      try {
        setLoadingIndex(true);
        const data = await quotationApi.getIndexData(
          standardSymbol,
          config.start_date,
          config.end_date
        );

        if (data && data.length > 0) {
          setIndexData(data);
        } else {
          console.warn('未获取到指数数据，将使用模拟数据');
          setIndexData([]);
        }
      } catch (error) {
        console.error('获取指数数据失败:', error);
        message.warning('获取基准指数数据失败，将使用模拟数据');
        setIndexData([]);
      } finally {
        setLoadingIndex(false);
      }
    };

    fetchIndexData();
  }, [config.start_date, config.end_date, config.standard_symbol]);

  const normalizeDateKey = (rawDate: any): string | null => {
    if (!rawDate) {
      return null;
    }

    const str = String(rawDate).trim();

    if (/^\d{8}$/.test(str)) {
      return str;
    }

    if (/^\d{4}-\d{2}-\d{2}/.test(str)) {
      return str.replace(/-/g, '').substring(0, 8);
    }

    if (/^\d{13}$/.test(str)) {
      return dayjs(Number(str)).format('YYYYMMDD');
    }

    const parsed = dayjs(str);
    if (parsed.isValid()) {
      return parsed.format('YYYYMMDD');
    }

    return null;
  };

  const getProfitDateKey = (item: ProfitData): string | null => {
    const rawDate =
      (item as any).date ??
      (item as any).trade_date ??
      (item as any).gmt_create_time ??
      (item as any).gmt_create ??
      (item as any).gmt_date ??
      (item as any).day;

    return normalizeDateKey(rawDate);
  };

  const { benchmarkNetValueMap, hasRealBenchmarkData } = useMemo(() => {
    if (!indexData || indexData.length === 0) {
      return {
        benchmarkNetValueMap: new Map<string, number>(),
        hasRealBenchmarkData: false,
      };
    }

    const entries = indexData
      .map((item: any) => {
        const rawDate =
          item.date ??
          item.trade_date ??
          item.tradeTime ??
          item.time ??
          item.trading_day ??
          item.tradingDate ??
          item.gmt_create_time;

        const dateKey = normalizeDateKey(rawDate);
        const closeValue = Number(
          item.close ??
            item.Close ??
            item.price ??
            item.last ??
            item.endPrice ??
            item.end_price ??
            item.latest
        );

        if (!dateKey || !isFinite(closeValue) || closeValue <= 0) {
          return null;
        }

        return { dateKey, close: closeValue };
      })
      .filter(Boolean) as { dateKey: string; close: number }[];

    if (entries.length === 0) {
      return {
        benchmarkNetValueMap: new Map<string, number>(),
        hasRealBenchmarkData: false,
      };
    }

    entries.sort((a, b) => a.dateKey.localeCompare(b.dateKey));

    const baseEntry = entries.find((entry) => entry.close > 0);
    if (!baseEntry) {
      return {
        benchmarkNetValueMap: new Map<string, number>(),
        hasRealBenchmarkData: false,
      };
    }

    const baseClose = baseEntry.close;
    const netValueMap = new Map<string, number>();

    entries.forEach(({ dateKey, close }) => {
      if (close > 0 && isFinite(close)) {
        netValueMap.set(dateKey, close / baseClose);
      }
    });

    return {
      benchmarkNetValueMap: netValueMap,
      hasRealBenchmarkData: netValueMap.size > 0,
    };
  }, [indexData]);

  // 过滤数据根据日期范围
  const getFilteredData = () => {
    const validProfitData = profitData.filter((item) => Boolean(getProfitDateKey(item)));

    if (!dateRange) {
      return validProfitData;
    }

    const [start, end] = dateRange;
    const startDay = start.startOf('day');
    const endDay = end.endOf('day');

    return validProfitData.filter((item) => {
      const dateKey = getProfitDateKey(item);
      if (!dateKey) {
        return false;
      }
      const itemDate = dayjs(dateKey, 'YYYYMMDD');
      return !itemDate.isBefore(startDay) && !itemDate.isAfter(endDay);
    });
  };

  const filteredData = getFilteredData();

  // 格式化数字，处理 Infinity 和 NaN
  const formatNumber = (num: number, precision: number = 4): string => {
    if (isNaN(num) || !isFinite(num) || num === Infinity || num === -Infinity) {
      return '1.0000';
    }
    return num.toFixed(precision);
  };

  const getChartOption = () => {
    if (filteredData.length === 0) {
      return {
        title: { text: '暂无数据', left: 'center', top: 'center' }
      };
    }

    const initialCapital = (config.start_capital || 1000) * 10000;
    if (initialCapital <= 0) {
      return {
        title: { text: '初始资金配置错误', left: 'center', top: 'center' }
      };
    }
    
    // 日期序列
    const dates = filteredData.map(item => {
      const dateKey = getProfitDateKey(item);
      return dateKey ? dayjs(dateKey, 'YYYYMMDD').format('YYYY-MM-DD') : '';
    });

    // 策略净值曲线（净值 = 当前资产 / 初始资金）
    const strategyEquity = filteredData.map((item, index) => {
      let value = Number(item.total_value ?? item.total_profit ?? item.strategy_profit);
      
      // 如果值为0、负数或无效，使用初始资金
      if (!value || value <= 0 || !isFinite(value)) {
        value = initialCapital;
      }
      
      // 特别处理第一个数据点：如果第一个点的值异常小（小于初始资金的50%），则认为是数据错误，使用初始资金
      if (index === 0 && value < initialCapital * 0.5) {
        value = initialCapital;
      }
      
      const netValue = value / initialCapital;
      return formatNumber(netValue, 4);
    });

    // 基准净值曲线（从真实指数数据计算，或使用模拟数据）
    let lastBenchmarkNetValue: number | null = hasRealBenchmarkData ? 1 : null;
    const benchmarkEquity = filteredData.map((item, index) => {
      if (hasRealBenchmarkData) {
        const dateKey = getProfitDateKey(item);
        const netValueForDate = dateKey ? benchmarkNetValueMap.get(dateKey) : undefined;

        if (typeof netValueForDate === 'number' && isFinite(netValueForDate) && netValueForDate > 0) {
          lastBenchmarkNetValue = netValueForDate;
          return formatNumber(netValueForDate, 4);
        }

        if (lastBenchmarkNetValue !== null) {
          return formatNumber(lastBenchmarkNetValue, 4);
        }
      }

      // 如果没有真实数据，使用模拟数据（假设年化8%的线性增长）
      const days = index;
      const dailyReturn = 0.08 / 252;
      const netValue = 1 + dailyReturn * days;
      return formatNumber(netValue, 4);
    });

    // 超额收益曲线（策略净值 - 基准净值）
    const excessEquity = strategyEquity.map((val, idx) => {
      const strategyVal = parseFloat(val);
      const benchmarkVal = parseFloat(benchmarkEquity[idx]);
      const excess = strategyVal - benchmarkVal;
      return formatNumber(excess, 4);
    });

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
        yAxisIndex: 1, // 使用第二个Y轴
      });
      legendData.push('超额收益');
    }

    // 计算累计收益率用于副标题
    const latestNetValue = strategyEquity.length > 0 ? parseFloat(strategyEquity[strategyEquity.length - 1]) : 1;
    const totalReturn = isFinite(latestNetValue) && latestNetValue > 0 
      ? ((latestNetValue - 1) * 100).toFixed(2)
      : '0.00';

    // 判断是否使用了真实指数数据
    const usingRealIndexData = hasRealBenchmarkData;
    const benchmarkName = config.standard_symbol || '000001.SH';
    
    // 计算净值Y轴范围
    const calculateNetValueYAxisRange = () => {
      const netValueData: number[] = [];
      
      if (showStrategy) {
        strategyEquity.forEach(v => {
          const num = parseFloat(v);
          if (isFinite(num)) netValueData.push(num);
        });
      }
      if (showBenchmark) {
        benchmarkEquity.forEach(v => {
          const num = parseFloat(v);
          if (isFinite(num)) netValueData.push(num);
        });
      }
      
      if (netValueData.length === 0) {
        return { min: 0.9, max: 1.1 };
      }
      
      const minValue = Math.min(...netValueData);
      const maxValue = Math.max(...netValueData);
      const range = maxValue - minValue;
      
      // 如果范围很小（比如都在1.0附近），则放大显示
      if (range < 0.1) {
        const center = (minValue + maxValue) / 2;
        const padding = Math.max(range * 3, 0.02); // 至少2%的边距，放大3倍范围
        return {
          min: Math.max(0, center - padding),
          max: center + padding
        };
      } else {
        const padding = range * 0.1;
        return {
          min: Math.max(0, minValue - padding),
          max: maxValue + padding
        };
      }
    };
    
    // 计算超额收益Y轴范围
    const calculateExcessYAxisRange = () => {
      const excessData: number[] = [];
      
      if (showExcess) {
        excessEquity.forEach(v => {
          const num = parseFloat(v);
          if (isFinite(num)) excessData.push(num);
        });
      }
      
      if (excessData.length === 0) {
        return { min: -0.1, max: 0.1 };
      }
      
      const minValue = Math.min(...excessData);
      const maxValue = Math.max(...excessData);
      const range = maxValue - minValue;
      
      // 如果范围很小，放大显示
      if (range < 0.1) {
        const center = (minValue + maxValue) / 2;
        const padding = Math.max(range * 3, 0.01); // 至少1%的边距
        return {
          min: center - padding,
          max: center + padding
        };
      } else {
        const padding = range * 0.1;
        return {
          min: minValue - padding,
          max: maxValue + padding
        };
      }
    };
    
    const netValueYAxisRange = calculateNetValueYAxisRange();
    const excessYAxisRange = calculateExcessYAxisRange();
    
    return {
      title: {
        text: '策略净值曲线',
        left: 'center',
        top: 10,
        textStyle: { 
          fontSize: 16, 
          fontWeight: 'bold',
          color: '#333'
        },
        subtext: `累计收益率: ${totalReturn}% | 基准: ${benchmarkName} ${usingRealIndexData ? '' : '(模拟数据)'}`,
        subtextStyle: {
          fontSize: 12,
          color: '#666',
          lineHeight: 20
        }
      },
      tooltip: {
        trigger: 'axis',
        formatter: (params: any) => {
          if (!params || params.length === 0) return '';
          let content = params[0].name + '<br/>';
          params.forEach((param: any) => {
            const value = parseFloat(param.value);
            if (!isFinite(value)) {
              content += `${param.marker} ${param.seriesName}: 无效数据<br/>`;
              return;
            }
            // 对于净值和基准净值，直接显示净值，对于超额收益显示百分比
            if (param.seriesName.includes('净值')) {
              const returnRate = (value - 1) * 100;
              const returnRateStr = isFinite(returnRate) ? returnRate.toFixed(2) : '0.00';
              content += `${param.marker} ${param.seriesName}: ${formatNumber(value, 4)} (${returnRate >= 0 ? '+' : ''}${returnRateStr}%)<br/>`;
            } else {
              const returnRate = value * 100;
              const returnRateStr = isFinite(returnRate) ? returnRate.toFixed(2) : '0.00';
              content += `${param.marker} ${param.seriesName}: ${returnRate >= 0 ? '+' : ''}${returnRateStr}%<br/>`;
            }
          });
          return content;
        },
      },
      legend: {
        data: legendData,
        top: 50,
        right: 20,
        itemGap: 20,
        textStyle: {
          fontSize: 12
        }
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '10%',
        top: '100px',
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
      yAxis: [
        {
          type: 'value',
          name: '净值',
          position: 'left',
          min: netValueYAxisRange.min,
          max: netValueYAxisRange.max,
          scale: false,  // 使用自定义范围，不使用自动缩放
          axisLabel: {
            formatter: (value: number) => {
              // 如果值接近1.0，显示更多小数位以便看清波动
              if (Math.abs(value - 1.0) < 0.1) {
                return value.toFixed(4);
              }
              return value.toFixed(2);
            }
          },
          splitLine: {
            lineStyle: {
              type: 'dashed',
              color: '#e0e0e0'
            },
            show: true
          },
          splitNumber: 8,  // 增加分割线数量，使刻度更精细
        },
        ...(showExcess ? [{
          type: 'value',
          name: '超额收益',
          position: 'right',
          min: excessYAxisRange.min,
          max: excessYAxisRange.max,
          scale: false,
          axisLabel: {
            formatter: (value: number) => {
              // 超额收益显示为百分比（数据已经是小数形式，如-0.0017表示-0.17%）
              return (value * 100).toFixed(2) + '%';
            }
          },
          splitLine: {
            show: false  // 右侧Y轴不显示分割线，避免与左侧重叠
          },
          splitNumber: 6,
        }] : [])
      ],
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
    
    const initialCapital = (config.start_capital || 1000) * 10000;
    if (initialCapital <= 0) {
      return {
        totalReturn: 0,
        maxDrawdown: 0,
        volatility: 0,
        latestValue: initialCapital,
      };
    }
    
    const values = filteredData.map(item => {
      const value = Number(item.total_value ?? item.total_profit ?? item.strategy_profit ?? initialCapital);
      // 确保值是有效的正数
      return (value > 0 && isFinite(value)) ? value : initialCapital;
    });
    
    const latestValue = values[values.length - 1];
    let totalReturn = 0;
    if (initialCapital > 0 && isFinite(latestValue) && isFinite(initialCapital)) {
      totalReturn = ((latestValue - initialCapital) / initialCapital) * 100;
      if (!isFinite(totalReturn)) totalReturn = 0;
    }
    
    // 计算最大回撤
    let maxDrawdown = 0;
    let peak = values[0];
    if (peak > 0 && isFinite(peak)) {
      for (const value of values) {
        if (value > peak && isFinite(value)) peak = value;
        if (peak > 0 && isFinite(value)) {
          const drawdown = ((peak - value) / peak) * 100;
          if (isFinite(drawdown) && drawdown > maxDrawdown) {
            maxDrawdown = drawdown;
          }
        }
      }
    }
    
    // 计算波动率
    let volatility = 0;
    const validReturns: number[] = [];
    for (let i = 1; i < values.length; i++) {
      const prevValue = values[i - 1];
      const currValue = values[i];
      if (prevValue > 0 && isFinite(prevValue) && isFinite(currValue)) {
        const ret = (currValue - prevValue) / prevValue;
        if (isFinite(ret)) {
          validReturns.push(ret);
        }
      }
    }
    
    if (validReturns.length > 0) {
      const avgReturn = validReturns.reduce((a, b) => a + b, 0) / validReturns.length;
      if (isFinite(avgReturn)) {
        const variance = validReturns.reduce((sum, r) => {
          const diff = r - avgReturn;
          return sum + (diff * diff);
        }, 0) / validReturns.length;
        if (isFinite(variance) && variance >= 0) {
          volatility = Math.sqrt(variance) * Math.sqrt(252) * 100;
          if (!isFinite(volatility)) volatility = 0;
        }
      }
    }
    
    return {
      totalReturn,
      maxDrawdown,
      volatility,
      latestValue: isFinite(latestValue) ? latestValue : initialCapital,
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
                  color: metrics.totalReturn >= 0 ? '#ff4d4f' : '#52c41a',
                  marginTop: 4,
                }}>
                  {(() => {
                    const returnValue = isFinite(metrics.totalReturn) ? metrics.totalReturn : 0;
                    return (returnValue >= 0 ? '+' : '') + formatNumber(returnValue, 2) + '%';
                  })()}
                </div>
              </div>
            </Col>
            <Col span={6}>
              <div style={{ textAlign: 'center', padding: '8px', background: '#fff', borderRadius: '4px' }}>
                <div style={{ fontSize: 12, color: '#999' }}>最大回撤</div>
                <div style={{ fontSize: 18, fontWeight: 'bold', color: '#ff4d4f', marginTop: 4 }}>
                  {formatNumber(isFinite(metrics.maxDrawdown) ? metrics.maxDrawdown : 0, 2)}%
                </div>
              </div>
            </Col>
            <Col span={6}>
              <div style={{ textAlign: 'center', padding: '8px', background: '#fff', borderRadius: '4px' }}>
                <div style={{ fontSize: 12, color: '#999' }}>年化波动率</div>
                <div style={{ fontSize: 18, fontWeight: 'bold', color: '#1890ff', marginTop: 4 }}>
                  {formatNumber(isFinite(metrics.volatility) ? metrics.volatility : 0, 2)}%
                </div>
              </div>
            </Col>
            <Col span={6}>
              <div style={{ textAlign: 'center', padding: '8px', background: '#fff', borderRadius: '4px' }}>
                <div style={{ fontSize: 12, color: '#999' }}>当前净值</div>
                <div style={{ fontSize: 18, fontWeight: 'bold', color: '#722ed1', marginTop: 4 }}>
                  {(() => {
                    const startCapital = (config.start_capital || 1000) * 10000;
                    if (startCapital <= 0 || !isFinite(metrics.latestValue) || !isFinite(startCapital)) {
                      return '1.0000';
                    }
                    const netValue = metrics.latestValue / startCapital;
                    return formatNumber(netValue, 4);
                  })()}
                </div>
              </div>
            </Col>
          </Row>
        )}
      </div>
      
      {/* 图表 */}
      {loadingIndex ? (
        <div style={{ height: 450, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Spin tip="正在加载基准指数数据..." />
        </div>
      ) : filteredData.length > 0 ? (
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

