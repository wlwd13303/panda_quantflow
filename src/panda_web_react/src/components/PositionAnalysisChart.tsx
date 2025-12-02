import React, { useState, useEffect } from 'react';
import { Card, DatePicker, Space, Empty, Spin, message, Select, Row, Col } from 'antd';
import ReactECharts from 'echarts-for-react';
import dayjs from 'dayjs';
import { quotationApi, backtestApi } from '@/services/api';
import type { PositionData, KLineData } from '@/types';

const { RangePicker } = DatePicker;
const { Option } = Select;

interface PositionAnalysisChartProps {
  backtestId: string; // 回测ID，用于获取仓位数据
  config: {
    start_date: string;
    end_date: string;
    standard_symbol?: string; // 基准指数代码
    strategy_symbols: string[]; // 策略交易的股票代码列表
  };
}

const PositionAnalysisChart: React.FC<PositionAnalysisChartProps> = ({ backtestId, config }) => {
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs, dayjs.Dayjs] | null>(null);
  const [loadingOverallPosition, setLoadingOverallPosition] = useState(false);
  const [overallPositionData, setOverallPositionData] = useState<PositionData[]>([]);
  const [indexData, setIndexData] = useState<any[]>([]);
  const [loadingIndex, setLoadingIndex] = useState(false);

  const [selectedStock, setSelectedStock] = useState<string | undefined>(undefined);
  const [loadingStockPosition, setLoadingStockPosition] = useState(false);
  const [stockPositionData, setStockPositionData] = useState<PositionData[]>([]);
  const [stockKLineData, setStockKLineData] = useState<KLineData[]>([]);
  const [loadingKLine, setLoadingKLine] = useState(false);

  useEffect(() => {
    if (config.strategy_symbols && config.strategy_symbols.length > 0) {
      setSelectedStock(config.strategy_symbols[0]); // 默认选中第一个股票
    }
  }, [config.strategy_symbols]);

  // 获取账户整体仓位数据
  useEffect(() => {
    const fetchOverallPositionData = async () => {
      if (!backtestId || !config.start_date || !config.end_date) return;

      try {
        setLoadingOverallPosition(true);
        const result = await backtestApi.getPositionData(
          backtestId
        );
        const data = result.items || [];
        if (data && data.length > 0) {
          setOverallPositionData(data);
        } else {
          console.warn('未获取到账户整体仓位数据');
          setOverallPositionData([]);
        }
      } catch (error) {
        console.error('获取账户整体仓位数据失败:', error);
        message.error('获取账户整体仓位数据失败');
        setOverallPositionData([]);
      } finally {
        setLoadingOverallPosition(false);
      }
    };
    fetchOverallPositionData();
  }, [backtestId, config.start_date, config.end_date]);

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

  // 获取个股仓位数据
  useEffect(() => {
    const fetchStockPositionData = async () => {
      if (!backtestId || !selectedStock || !config.start_date || !config.end_date) return;

      try {
        setLoadingStockPosition(true);
        const result = await backtestApi.getPositionData(
          backtestId
        );
        const data = result.items || [];
        if (data && data.length > 0) {
          setStockPositionData(data);
        } else {
          console.warn(`未获取到 ${selectedStock} 的个股仓位数据`);
          setStockPositionData([]);
        }
      } catch (error) {
        console.error(`获取 ${selectedStock} 的个股仓位数据失败:`, error);
        message.error(`获取 ${selectedStock} 的个股仓位数据失败`);
        setStockPositionData([]);
      } finally {
        setLoadingStockPosition(false);
      }
    };
    fetchStockPositionData();
  }, [backtestId, selectedStock, config.start_date, config.end_date]);

  // 获取个股K线数据
  useEffect(() => {
    const fetchStockKLineData = async () => {
      if (!selectedStock || !config.start_date || !config.end_date) return;

      try {
        setLoadingKLine(true);
        const data = await quotationApi.getStockKLineData(
          selectedStock,
          config.start_date,
          config.end_date
        );
        if (data && data.length > 0) {
          setStockKLineData(data);
        } else {
          console.warn(`未获取到 ${selectedStock} 的K线数据`);
          setStockKLineData([]);
        }
      } catch (error) {
        console.error(`获取 ${selectedStock} 的K线数据失败:`, error);
        message.error(`获取 ${selectedStock} 的K线数据失败`);
        setStockKLineData([]);
      } finally {
        setLoadingKLine(false);
      }
    };
    fetchStockKLineData();
  }, [selectedStock, config.start_date, config.end_date]);

  // 过滤数据根据日期范围
  const getFilteredOverallPositionData = () => {
    if (!dateRange) return overallPositionData;
    const [start, end] = dateRange;
    return overallPositionData.filter(item => {
      const dateStr = String(item.date || item.trade_date || '').substring(0, 8);
      const itemDate = dayjs(dateStr, 'YYYYMMDD');
      return itemDate.isAfter(start.subtract(1, 'day')) && itemDate.isBefore(end.add(1, 'day'));
    });
  };

  const getFilteredStockPositionData = () => {
    if (!dateRange) return stockPositionData;
    const [start, end] = dateRange;
    return stockPositionData.filter(item => {
      const dateStr = String(item.date || item.trade_date || '').substring(0, 8);
      const itemDate = dayjs(dateStr, 'YYYYMMDD');
      return itemDate.isAfter(start.subtract(1, 'day')) && itemDate.isBefore(end.add(1, 'day'));
    });
  };

  const getFilteredIndexData = () => {
    if (!dateRange) return indexData;
    const [start, end] = dateRange;
    return indexData.filter(item => {
      const dateStr = String(item.date || item.trade_date || '').substring(0, 8);
      const itemDate = dayjs(dateStr, 'YYYYMMDD');
      return itemDate.isAfter(start.subtract(1, 'day')) && itemDate.isBefore(end.add(1, 'day'));
    });
  };

  const getFilteredKLineData = () => {
    if (!dateRange) return stockKLineData;
    const [start, end] = dateRange;
    return stockKLineData.filter(item => {
      const dateStr = String(item.date || item.trade_date || '').substring(0, 8);
      const itemDate = dayjs(dateStr, 'YYYYMMDD');
      return itemDate.isAfter(start.subtract(1, 'day')) && itemDate.isBefore(end.add(1, 'day'));
    });
  };

  const filteredOverallPositionData = getFilteredOverallPositionData();
  const filteredIndexData = getFilteredIndexData();
  const filteredStockPositionData = getFilteredStockPositionData();
  const filteredKLineData = getFilteredKLineData();

  // 格式化数字
  const formatNumber = (num: number, precision: number = 2): string => {
    if (isNaN(num) || !isFinite(num)) {
      return '0.00';
    }
    return num.toFixed(precision);
  };

  // 获取账户整体仓位图表配置
  const getOverallPositionChartOption = () => {
    if (filteredOverallPositionData.length === 0 && filteredIndexData.length === 0) {
      return { title: { text: '暂无账户整体仓位数据', left: 'center', top: 'center' } };
    }

    const dates = filteredOverallPositionData.map(item => dayjs(String(item.date || item.trade_date || '').substring(0, 8), 'YYYYMMDD').format('YYYY-MM-DD'));

    const overallPositionRatio = filteredOverallPositionData.map(item => formatNumber(item.position_ratio ?? 0, 4));

    // 对齐指数数据和仓位数据日期
    const alignedIndexData: number[] = [];
    if (filteredIndexData.length > 0) {
      const startIndexValue = Number(filteredIndexData[0].close || filteredIndexData[0].Close || filteredIndexData[0].price || filteredIndexData[0].last || 1);
      filteredOverallPositionData.forEach(posItem => {
        const posDateStr = String(posItem.date || posItem.trade_date || '').substring(0, 8);
        const indexItem = filteredIndexData.find(idx => {
          const idxDateStr = String(idx.date || idx.trade_date || '').substring(0, 8);
          return idxDateStr === posDateStr;
        });

        if (indexItem && startIndexValue > 0) {
          const currentIndexValue = Number(indexItem.close || indexItem.Close || indexItem.price || indexItem.last || 0);
          alignedIndexData.push(currentIndexValue / startIndexValue); // 归一化
        } else {
          alignedIndexData.push(1); // 填充默认值
        }
      });
    } else {
      // 如果没有指数数据，则使用模拟数据填充
      filteredOverallPositionData.forEach(() => alignedIndexData.push(1));
    }
    
    const legendData = ['账户仓位比例', '基准指数净值'];

    return {
      title: {
        text: '账户整体仓位与指数曲线',
        left: 'center',
        top: 10,
        textStyle: { fontSize: 16, fontWeight: 'bold' },
      },
      tooltip: {
        trigger: 'axis',
        formatter: (params: any) => {
          if (!params || params.length === 0) return '';
          let content = params[0].name + '<br/>';
          params.forEach((param: any) => {
            if (param.seriesName === '账户仓位比例') {
              content += `${param.marker} ${param.seriesName}: ${formatNumber(parseFloat(param.value) * 100, 2)}%<br/>`;
            } else if (param.seriesName === '基准指数净值') {
              const returnRate = (parseFloat(param.value) - 1) * 100;
              content += `${param.marker} ${param.seriesName}: ${formatNumber(parseFloat(param.value), 4)} (${returnRate >= 0 ? '+' : ''}${formatNumber(returnRate, 2)}%)<br/>`;
            }
          });
          return content;
        },
      },
      legend: {
        data: legendData,
        top: 50,
        right: 20,
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
        data: dates,
        boundaryGap: false,
        axisLabel: {
          rotate: 30,
          interval: Math.floor(dates.length / 10),
        },
      },
      yAxis: [
        {
          type: 'value',
          name: '仓位比例',
          min: 0,
          max: 1,
          axisLabel: { formatter: '{value}%' },
          splitLine: { show: true, lineStyle: { type: 'dashed' } },
        },
        {
          type: 'value',
          name: '指数净值',
          position: 'right',
          axisLabel: { formatter: '{value}' },
          splitLine: { show: false },
        },
      ],
      series: [
        {
          name: '账户仓位比例',
          type: 'line',
          data: overallPositionRatio.map(v => parseFloat(v) * 100), // 显示为百分比
          smooth: true,
          lineStyle: { color: '#5470c6', width: 2 },
          showSymbol: false,
          yAxisIndex: 0,
        },
        {
          name: '基准指数净值',
          type: 'line',
          data: alignedIndexData,
          smooth: true,
          lineStyle: { color: '#fac858', width: 2, type: 'dashed' },
          showSymbol: false,
          yAxisIndex: 1,
        },
      ],
      dataZoom: [
        { type: 'inside', start: 0, end: 100 },
        { type: 'slider', start: 0, end: 100, height: 20, bottom: 10 },
      ],
    };
  };

  // 获取个股仓位与K线图表配置
  const getStockPositionKLineChartOption = () => {
    if (filteredStockPositionData.length === 0 && filteredKLineData.length === 0) {
      return { title: { text: `暂无 ${selectedStock || ''} 个股仓位及K线数据`, left: 'center', top: 'center' } };
    }

    const dates = filteredKLineData.map(item => dayjs(String(item.date || item.trade_date || '').substring(0, 8), 'YYYYMMDD').format('YYYY-MM-DD'));
    const klineData = filteredKLineData.map(item => [
      item.open, item.close, item.low, item.high
    ]);
    const volumes = filteredKLineData.map(item => item.volume);

    // 对齐个股仓位数据和K线数据日期
    const alignedStockPositionRatio: number[] = [];
    filteredKLineData.forEach(klineItem => {
      const klineDateStr = String(klineItem.date || klineItem.trade_date || '').substring(0, 8);
      const positionItem = filteredStockPositionData.find(pos => {
        const posDateStr = String(pos.date || pos.trade_date || '').substring(0, 8);
        return posDateStr === klineDateStr;
      });
      alignedStockPositionRatio.push(positionItem ? (positionItem.position_ratio ?? 0) : 0);
    });
    
    const legendData = ['K线', '成交量', '个股仓位比例'];

    return {
      title: {
        text: `${selectedStock || ''} 仓位与K线走势`,
        left: 'center',
        top: 10,
        textStyle: { fontSize: 16, fontWeight: 'bold' },
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'cross' },
        formatter: (params: any) => {
          if (!params || params.length === 0) return '';
          let content = params[0].name + '<br/>';
          params.forEach((param: any) => {
            if (param.seriesName === 'K线') {
              content += `${param.marker} 开: ${param.data[0]} 高: ${param.data[3]} 低: ${param.data[2]} 关: ${param.data[1]}<br/>`;
            } else if (param.seriesName === '成交量') {
              content += `${param.marker} ${param.seriesName}: ${formatNumber(param.value, 0)}<br/>`;
            } else if (param.seriesName === '个股仓位比例') {
              content += `${param.marker} ${param.seriesName}: ${formatNumber(parseFloat(param.value), 4)}<br/>`;
            }
          });
          return content;
        },
      },
      legend: {
        data: legendData,
        top: 50,
        right: 20,
      },
      grid: [
        { left: '3%', right: '4%', height: '50%', top: '100px', containLabel: true },
        { left: '3%', right: '4%', height: '15%', top: '65%', containLabel: true },
        { left: '3%', right: '4%', height: '15%', top: '80%', containLabel: true },
      ],
      xAxis: [
        { type: 'category', data: dates, scale: true, boundaryGap: false, axisLine: { onZero: false }, splitLine: { show: false }, axisTick: { show: false }, axisLabel: { show: false } },
        { type: 'category', gridIndex: 1, data: dates, scale: true, boundaryGap: false, axisLine: { onZero: false }, splitLine: { show: false }, axisTick: { show: false }, axisLabel: { show: false } },
        { type: 'category', gridIndex: 2, data: dates, scale: true, boundaryGap: false, axisLine: { onZero: false }, splitLine: { show: false }, axisTick: { show: false }, axisLabel: { rotate: 30, interval: Math.floor(dates.length / 10) } },
      ],
      yAxis: [
        { type: 'value', name: 'K线价格', scale: true, splitArea: { show: true }, gridIndex: 0 },
        { type: 'value', name: '成交量', gridIndex: 1, splitLine: { show: false }, axisLabel: { formatter: '{value}' } },
        { type: 'value', name: '仓位比例', gridIndex: 2, splitLine: { show: true, lineStyle: { type: 'dashed' } }, axisLabel: { formatter: '{value}%' }},
      ],
      dataZoom: [
        { type: 'inside', xAxisIndex: [0, 1, 2], start: 0, end: 100 },
        { type: 'slider', xAxisIndex: [0, 1, 2], start: 0, end: 100, height: 20, bottom: 10 },
      ],
      series: [
        {
          name: 'K线',
          type: 'candlestick',
          data: klineData,
          xAxisIndex: 0,
          yAxisIndex: 0,
        },
        {
          name: '成交量',
          type: 'bar',
          xAxisIndex: 1,
          yAxisIndex: 1,
          data: volumes,
          itemStyle: {
            color: (params: any) => {
              const dataIndex = params.dataIndex;
              const open = klineData[dataIndex][0];
              const close = klineData[dataIndex][1];
              return close > open ? '#ef232a' : '#14b143'; // 涨跌颜色
            },
          },
        },
        {
          name: '个股仓位比例',
          type: 'line',
          xAxisIndex: 2,
          yAxisIndex: 2,
          data: alignedStockPositionRatio.map(v => v * 100), // 显示为百分比
          smooth: true,
          lineStyle: { color: '#722ed1', width: 2 },
          showSymbol: false,
        },
      ],
    };
  };

  return (
    <Card 
      styles={{ body: { padding: '16px' } }}
      style={{ height: '100%' }}
    >
      <div style={{ marginBottom: 16, background: '#fafafa', padding: '12px', borderRadius: '4px' }}>
        <Row justify="space-between" align="middle" gutter={[16, 8]}>
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
          <Col>
            <Space>
              <span style={{ fontSize: 12, color: '#666' }}>选择股票：</span>
              <Select
                value={selectedStock}
                style={{ width: 120 }}
                onChange={(value) => setSelectedStock(value)}
                size="small"
                showSearch
                optionFilterProp="children"
                filterOption={(input, option) => {
                  const children = String(option?.children || '');
                  return children.toLowerCase().indexOf(input.toLowerCase()) >= 0;
                }}
              >
                {config.strategy_symbols.map(symbol => (
                  <Option key={symbol} value={symbol}>{symbol}</Option>
                ))}
              </Select>
            </Space>
          </Col>
        </Row>
      </div>

      <Row gutter={[16, 16]}>
        <Col span={24}>
          <Card title="账户整体仓位分析" size="small" style={{ marginBottom: 16 }}>
            {loadingOverallPosition || loadingIndex ? (
              <div style={{ height: 400, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Spin tip="正在加载账户整体仓位数据..." />
              </div>
            ) : (filteredOverallPositionData.length > 0 || filteredIndexData.length > 0) ? (
              <ReactECharts 
                option={getOverallPositionChartOption()} 
                style={{ height: 400 }}
                opts={{ renderer: 'canvas' }}
              />
            ) : (
              <div style={{ height: 400, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Empty description="暂无账户整体仓位数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />
              </div>
            )}
          </Card>
        </Col>
        <Col span={24}>
          <Card title="个股仓位分析" size="small">
            {loadingStockPosition || loadingKLine ? (
              <div style={{ height: 450, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Spin tip={`正在加载 ${selectedStock || ''} 的仓位及K线数据...`} />
              </div>
            ) : (filteredStockPositionData.length > 0 || filteredKLineData.length > 0) ? (
              <ReactECharts 
                option={getStockPositionKLineChartOption()} 
                style={{ height: 450 }}
                opts={{ renderer: 'canvas' }}
              />
            ) : (
              <div style={{ height: 450, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Empty description={`暂无 ${selectedStock || ''} 的仓位及K线数据`} image={Empty.PRESENTED_IMAGE_SIMPLE} />
              </div>
            )}
          </Card>
        </Col>
      </Row>
    </Card>
  );
};

export default PositionAnalysisChart;
