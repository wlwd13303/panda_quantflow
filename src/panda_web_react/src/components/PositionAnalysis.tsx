import React, { useState, useEffect, useMemo } from 'react';
import {
  Card,
  Select,
  DatePicker,
  Row,
  Col,
  Space,
  Empty,
  Spin,
  Alert,
  Typography,
  Tooltip,
  Tabs,
  Checkbox,
  Statistic,
} from 'antd';
import {
  InfoCircleOutlined,
  StockOutlined,
  LineChartOutlined,
  BarChartOutlined,
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import type { PositionData, ProfitData, BacktestConfig } from '@/types';
import { quotationApi } from '@/services/api';

const { RangePicker } = DatePicker;
const { Title, Text } = Typography;
const { TabPane } = Tabs;

interface PositionAnalysisProps {
  positionData: PositionData[];
  profitData: ProfitData[];
  config: BacktestConfig;
}

interface KLineData {
  date: string;
  open: number;
  close: number;
  low: number;
  high: number;
  volume: number;
}

const PositionAnalysis: React.FC<PositionAnalysisProps> = ({
  positionData,
  profitData,
  config,
}) => {
  const [selectedSymbol, setSelectedSymbol] = useState<string>('');
  const [dateRange, setDateRange] = useState<[string, string] | null>(null);
  const [loading, setLoading] = useState(false);
  const [klineData, setKlineData] = useState<KLineData[]>([]);
  const [indexData, setIndexData] = useState<any[]>([]);
  const [showIndex, setShowIndex] = useState(true);
  const [showPosition, setShowPosition] = useState(true);
  const [showKLine, setShowKLine] = useState(true);
  const [showStockPosition, setShowStockPosition] = useState(true);

  // 提取所有唯一的股票代码
  const symbols = Array.from(
    new Set(
      positionData
        .map((p) => p.symbol || p.contract_code || p.code)
        .filter(Boolean)
    )
  ).sort();

  // 计算总仓位数据（按日期聚合）
  const totalPositionData = useMemo(() => {
    const positionByDate = new Map<string, { date: string; totalValue: number; count: number; symbols: Set<string> }>();

    positionData.forEach((pos) => {
      const date = pos.date || pos.gmt_create || '';
      if (!date) return;

      const dateStr = date.length === 8 ? date : date.substring(0, 8);
      const marketValue = Number(pos.market_value || 0);
      const symbol = pos.symbol || pos.contract_code || pos.code || '';

      if (!positionByDate.has(dateStr)) {
        positionByDate.set(dateStr, { date: dateStr, totalValue: 0, count: 0, symbols: new Set() });
      }

      const existing = positionByDate.get(dateStr)!;
      existing.totalValue += marketValue;
      existing.count += 1;
      if (symbol) {
        existing.symbols.add(symbol);
      }
    });

    return Array.from(positionByDate.values())
      .map(item => ({
        date: item.date,
        totalValue: item.totalValue,
        count: item.count,
        symbolCount: item.symbols.size, // 持仓股票数量
      }))
      .sort((a, b) => a.date.localeCompare(b.date));
  }, [positionData]);

  // 获取指数数据
  useEffect(() => {
    const fetchIndexData = async () => {
      const standardSymbol = config.standard_symbol || '000001.SH';
      if (!config.start_date || !config.end_date) {
        return;
      }

      try {
        setLoading(true);
        const data = await quotationApi.getIndexData(
          standardSymbol,
          config.start_date,
          config.end_date
        );

        if (data && data.length > 0) {
          setIndexData(data);
        }
      } catch (error) {
        console.error('获取指数数据失败:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchIndexData();
  }, [config.start_date, config.end_date, config.standard_symbol]);

  // 获取个股K线数据
  const fetchStockKLineData = async (symbol: string) => {
    if (!symbol) {
      setKlineData([]);
      return;
    }

    setLoading(true);

    try {
      const symbolPositions = positionData.filter(
        (p) => (p.symbol || p.contract_code || p.code) === symbol
      );

      if (symbolPositions.length === 0) {
        setKlineData([]);
        setLoading(false);
        return;
      }

      // 获取持仓日期范围
      const dates = symbolPositions
        .map((p) => p.date || p.gmt_create || '')
        .filter(Boolean)
        .sort();
      const startDate = dates[0];
      const endDate = dateRange ? dateRange[1] : dates[dates.length - 1];

      // 调用API获取K线数据
      const apiData = await quotationApi.getStockKLineData(symbol, startDate, endDate);

      // 转换API数据格式
      const klineData: KLineData[] = apiData
        .map((item: any) => ({
          date: item.date || item.trade_date?.toString() || '',
          open: Number(item.open || 0),
          close: Number(item.close || 0),
          high: Number(item.high || 0),
          low: Number(item.low || 0),
          volume: Number(item.volume || 0),
        }))
        .filter((item: KLineData) => item.date.length === 8);

      // 按日期排序
      klineData.sort((a, b) => a.date.localeCompare(b.date));

      setKlineData(klineData);
    } catch (error) {
      console.error('获取K线数据失败:', error);
      setKlineData([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (selectedSymbol) {
      fetchStockKLineData(selectedSymbol);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedSymbol, dateRange]);

  // 过滤数据
  const getFilteredData = (data: any[]) => {
    if (!dateRange) return data;

    const [start, end] = dateRange;
    return data.filter((item) => {
      const date = item.date || item.gmt_create || '';
      const dateStr = date.length === 8 ? date : date.substring(0, 8);
      return dateStr >= start && dateStr <= end;
    });
  };

  // 生成总仓位曲线图配置
  const getTotalPositionChartOption = () => {
    const filteredPositionData = getFilteredData(totalPositionData);

    if (filteredPositionData.length === 0) {
      return {
        title: { text: '暂无数据', left: 'center', top: 'center' },
      };
    }

    // 日期序列
    const dates = filteredPositionData.map((item) => {
      const dateStr = item.date;
      return `${dateStr.substring(0, 4)}-${dateStr.substring(4, 6)}-${dateStr.substring(6, 8)}`;
    });

    // 仓位价值序列
    const positionValues = filteredPositionData.map((item) => item.totalValue.toFixed(2));

    // 计算仓位率（仓位价值 / 总资产）
    const positionRatios = filteredPositionData.map((item) => {
      // 从profitData中找到对应日期的总资产
      const dateStr = item.date;
      const profitItem = profitData.find((p) => {
        const pDate = String(p.date || p.gmt_create_time || p.gmt_create || '').substring(0, 8);
        return pDate === dateStr;
      });

      if (profitItem) {
        const totalValue = Number(
          profitItem.total_value ?? profitItem.total_profit ?? profitItem.strategy_profit ?? 0
        );
        if (totalValue > 0) {
          return ((item.totalValue / totalValue) * 100).toFixed(2);
        }
      }
      return '0';
    });

    // 基准指数归一化数据
    let indexNormalized: string[] = [];
    if (indexData && indexData.length > 0 && showIndex) {
      const firstIndexClose = Number(
        indexData[0].close || indexData[0].Close || indexData[0].price || indexData[0].last || 1
      );

      indexNormalized = filteredPositionData.map((item) => {
        const dateStr = item.date;
        const indexItem = indexData.find((idx) => {
          const idxDate = String(idx.date || idx.trade_date || '').substring(0, 8);
          return idxDate === dateStr;
        });

        if (indexItem && firstIndexClose > 0) {
          const currentClose = Number(
            indexItem.close || indexItem.Close || indexItem.price || indexItem.last || 0
          );
          // 归一化到100（初始值=100，相对涨跌幅）
          return (((currentClose / firstIndexClose) * 100).toFixed(2));
        }

        return '100';
      });
    }

    const series: any[] = [];

    if (showPosition) {
      series.push({
        name: '仓位价值',
        type: 'line',
        data: positionValues,
        smooth: true,
        lineStyle: { color: '#5470c6', width: 2 },
        showSymbol: false,
        yAxisIndex: 0,
      });

      series.push({
        name: '仓位率',
        type: 'line',
        data: positionRatios,
        smooth: true,
        lineStyle: { color: '#91cc75', width: 2 },
        showSymbol: false,
        yAxisIndex: 1,
      });
    }

    if (showIndex && indexNormalized.length > 0) {
      series.push({
        name: '基准指数(归一化)',
        type: 'line',
        data: indexNormalized,
        smooth: true,
        lineStyle: { color: '#fac858', width: 2, type: 'dashed' },
        showSymbol: false,
        yAxisIndex: 2,
      });
    }

    return {
      title: {
        text: '总仓位曲线与指数对比',
        left: 'center',
        top: 10,
        textStyle: {
          fontSize: 16,
          fontWeight: 'bold',
          color: '#333',
        },
        subtext: '对比仓位变化与指数走势，判断整体择时能力',
        subtextStyle: {
          fontSize: 12,
          color: '#666',
        },
      },
      tooltip: {
        trigger: 'axis',
        formatter: (params: any) => {
          if (!params || params.length === 0) return '';
          let content = params[0].name + '<br/>';
          params.forEach((param: any) => {
            if (!param || param.value === null || param.value === undefined) return;
            if (param.seriesName === '仓位价值') {
              content += `${param.marker} ${param.seriesName}: ¥${parseFloat(param.value).toLocaleString()}<br/>`;
            } else if (param.seriesName === '仓位率') {
              content += `${param.marker} ${param.seriesName}: ${param.value}%<br/>`;
            } else if (param.seriesName === '基准指数(归一化)') {
              content += `${param.marker} ${param.seriesName}: ${param.value}<br/>`;
            }
          });
          return content;
        },
      },
      legend: {
        data: series.map((s) => s.name),
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
          name: '仓位价值(元)',
          position: 'left',
          axisLabel: {
            formatter: (value: number) => `¥${(value / 10000).toFixed(0)}万`,
          },
        },
        {
          type: 'value',
          name: '仓位率(%)',
          position: 'right',
          min: 0,
          max: 100,
          axisLabel: {
            formatter: (value: number) => `${value}%`,
          },
        },
        ...(showIndex && indexNormalized.length > 0
          ? [
              {
                type: 'value',
                name: '指数(归一化)',
                position: 'right',
                offset: 60,
                axisLabel: {
                  formatter: (value: number) => value.toFixed(0),
                },
              },
            ]
          : []),
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

  // 生成持仓数量与指数走势图配置
  const getStockCountIndexChartOption = () => {
    const filteredPositionData = getFilteredData(totalPositionData);

    if (filteredPositionData.length === 0) {
      return {
        title: { text: '暂无数据', left: 'center', top: 'center' },
      };
    }

    // 日期序列
    const dates = filteredPositionData.map((item) => {
      const dateStr = item.date;
      return `${dateStr.substring(0, 4)}-${dateStr.substring(4, 6)}-${dateStr.substring(6, 8)}`;
    });

    // 持仓股票数量序列
    const stockCounts = filteredPositionData.map((item) => item.symbolCount);

    // 基准指数归一化数据
    let indexNormalized: number[] = [];
    if (indexData && indexData.length > 0) {
      const firstIndexClose = Number(
        indexData[0].close || indexData[0].Close || indexData[0].price || indexData[0].last || 1
      );

      indexNormalized = filteredPositionData.map((item) => {
        const dateStr = item.date;
        const indexItem = indexData.find((idx) => {
          const idxDate = String(idx.date || idx.trade_date || '').substring(0, 8);
          return idxDate === dateStr;
        });

        if (indexItem && firstIndexClose > 0) {
          const currentClose = Number(
            indexItem.close || indexItem.Close || indexItem.price || indexItem.last || 0
          );
          // 归一化到100（初始值=100，相对涨跌幅）
          return (currentClose / firstIndexClose) * 100;
        }

        return 100;
      });
    }

    const series: any[] = [];

    // 持仓数量柱状图
    series.push({
      name: '持仓股票数量',
      type: 'bar',
      data: stockCounts,
      itemStyle: { color: '#5470c6' },
      yAxisIndex: 0,
      barMaxWidth: 30,
    });

    // 基准指数折线图
    if (indexNormalized.length > 0) {
      series.push({
        name: '基准指数(归一化)',
        type: 'line',
        data: indexNormalized,
        smooth: true,
        lineStyle: { color: '#fac858', width: 2 },
        showSymbol: false,
        yAxisIndex: 1,
      });
    }

    return {
      title: {
        text: '持仓数量与指数走势对比',
        left: 'center',
        top: 10,
        textStyle: {
          fontSize: 16,
          fontWeight: 'bold',
          color: '#333',
        },
        subtext: '分析持仓股票数量变化与指数走势的关系',
        subtextStyle: {
          fontSize: 12,
          color: '#666',
        },
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'cross',
        },
        formatter: (params: any) => {
          if (!params || params.length === 0) return '';
          let content = params[0].name + '<br/>';
          params.forEach((param: any) => {
            if (!param || param.value === null || param.value === undefined) return;
            if (param.seriesName === '持仓股票数量') {
              content += `${param.marker} ${param.seriesName}: ${param.value}只<br/>`;
            } else if (param.seriesName === '基准指数(归一化)') {
              const changePercent = param.value - 100;
              content += `${param.marker} ${param.seriesName}: ${param.value.toFixed(2)} (${changePercent >= 0 ? '+' : ''}${changePercent.toFixed(2)}%)<br/>`;
            }
          });
          return content;
        },
      },
      legend: {
        data: series.map((s) => s.name),
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
        boundaryGap: true,
        data: dates,
        axisLabel: {
          rotate: 30,
          interval: Math.floor(dates.length / 10),
        },
      },
      yAxis: [
        {
          type: 'value',
          name: '持仓股票数量(只)',
          position: 'left',
          minInterval: 1,
          axisLabel: {
            formatter: (value: number) => `${value}只`,
          },
        },
        {
          type: 'value',
          name: '指数(归一化)',
          position: 'right',
          axisLabel: {
            formatter: (value: number) => value.toFixed(0),
          },
        },
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

  // 生成个股仓位曲线图配置
  const getStockPositionChartOption = () => {
    if (!selectedSymbol) {
      return {
        title: { text: '请选择股票', left: 'center', top: 'center' },
      };
    }

    const symbolPositions = positionData.filter(
      (p) => (p.symbol || p.contract_code || p.code) === selectedSymbol
    );

    const filteredPositions = getFilteredData(symbolPositions);

    if (filteredPositions.length === 0) {
      return {
        title: { text: '暂无数据', left: 'center', top: 'center' },
      };
    }

    // 按日期聚合持仓数据（可能同一天有多条记录）
    const positionByDate = new Map<
      string,
      { date: string; volume: number; marketValue: number }
    >();

    filteredPositions.forEach((pos) => {
      const date = pos.date || pos.gmt_create || '';
      const dateStr = date.length === 8 ? date : date.substring(0, 8);
      const volume = Number(pos.volume || 0);
      const marketValue = Number(pos.market_value || 0);

      if (!positionByDate.has(dateStr)) {
        positionByDate.set(dateStr, { date: dateStr, volume: 0, marketValue: 0 });
      }

      const existing = positionByDate.get(dateStr)!;
      existing.volume += volume;
      existing.marketValue += marketValue;
    });

    const aggregatedPositions = Array.from(positionByDate.values()).sort((a, b) =>
      a.date.localeCompare(b.date)
    );

    // 日期序列
    const dates = aggregatedPositions.map((item) => {
      const dateStr = item.date;
      return `${dateStr.substring(0, 4)}-${dateStr.substring(4, 6)}-${dateStr.substring(6, 8)}`;
    });

    // 持仓量序列
    const volumes = aggregatedPositions.map((item) => item.volume);

    // 市值序列
    const marketValues = aggregatedPositions.map((item) => item.marketValue.toFixed(2));

    // K线数据
    let klineValues: any[] = [];
    let klineDates: string[] = [];

    if (klineData.length > 0 && showKLine) {
      klineDates = klineData.map((d) => {
        const date = d.date;
        return `${date.substring(0, 4)}-${date.substring(4, 6)}-${date.substring(6, 8)}`;
      });

      klineValues = klineData.map((d) => [d.open, d.close, d.low, d.high]);
    }

    // 合并日期（K线日期 + 持仓日期）
    const allDatesSet = new Set([...klineDates, ...dates]);
    const allDates = Array.from(allDatesSet).sort();

    // 对齐数据：持仓量和市值需要根据allDates填充
    const alignedVolumes = allDates.map((date) => {
      const index = dates.indexOf(date);
      return index !== -1 ? volumes[index] : null;
    });

    const alignedMarketValues = allDates.map((date) => {
      const index = dates.indexOf(date);
      return index !== -1 ? marketValues[index] : null;
    });

    const alignedKLineValues = allDates.map((date) => {
      const index = klineDates.indexOf(date);
      return index !== -1 ? klineValues[index] : null;
    });

    const series: any[] = [];

    // K线序列
    if (showKLine && klineData.length > 0) {
      series.push({
        name: 'K线',
        type: 'candlestick',
        data: alignedKLineValues,
        itemStyle: {
          color: '#ef5350',
          color0: '#26a69a',
          borderColor: '#ef5350',
          borderColor0: '#26a69a',
        },
        yAxisIndex: 0,
      });
    }

    // 持仓量序列
    if (showStockPosition) {
      series.push({
        name: '持仓量',
        type: 'bar',
        data: alignedVolumes,
        itemStyle: { color: '#5470c6' },
        yAxisIndex: 1,
      });

      series.push({
        name: '持仓市值',
        type: 'line',
        data: alignedMarketValues,
        smooth: true,
        lineStyle: { color: '#91cc75', width: 2 },
        showSymbol: false,
        yAxisIndex: 2,
      });
    }

    return {
      animation: true,
      title: {
        text: `${selectedSymbol} 持仓曲线与K线`,
        left: 'center',
        top: 10,
        textStyle: {
          fontSize: 16,
          fontWeight: 'bold',
          color: '#333',
        },
        subtext: '对比个股持仓与K线走势，判断个股择时能力',
        subtextStyle: {
          fontSize: 12,
          color: '#666',
        },
      },
      legend: {
        data: series.map((s) => s.name),
        top: 50,
        right: 20,
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'cross',
        },
        formatter: (params: any) => {
          if (!params || params.length === 0) return '';

          let result = `日期: ${params[0].axisValue}<br/>`;

          params.forEach((param: any) => {
            if (!param) return;
            
            if (param.seriesName === 'K线' && param.value && Array.isArray(param.value)) {
              const kline = param.value;
              if (kline.length >= 5 && kline[1] !== null && kline[2] !== null && kline[3] !== null && kline[4] !== null) {
                result += `开盘: ¥${Number(kline[1]).toFixed(2)}<br/>`;
                result += `收盘: ¥${Number(kline[2]).toFixed(2)}<br/>`;
                result += `最低: ¥${Number(kline[3]).toFixed(2)}<br/>`;
                result += `最高: ¥${Number(kline[4]).toFixed(2)}<br/>`;
              }
            } else if (param.seriesName === '持仓量' && param.value !== null && param.value !== undefined) {
              result += `${param.marker} 持仓量: ${Number(param.value).toLocaleString()}股<br/>`;
            } else if (param.seriesName === '持仓市值' && param.value !== null && param.value !== undefined) {
              result += `${param.marker} 持仓市值: ¥${parseFloat(param.value).toLocaleString()}<br/>`;
            }
          });

          return result;
        },
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '15%',
        top: '100px',
        containLabel: true,
      },
      xAxis: {
        type: 'category',
        data: allDates,
        scale: true,
        boundaryGap: true,
        axisLine: { onZero: false },
        splitLine: { show: false },
        axisLabel: {
          rotate: 30,
          interval: Math.floor(allDates.length / 10),
        },
      },
      yAxis: [
        {
          type: 'value',
          name: '股价(元)',
          position: 'left',
          scale: true,
        },
        {
          type: 'value',
          name: '持仓量(股)',
          position: 'right',
          axisLabel: {
            formatter: (value: number) => value.toLocaleString(),
          },
        },
        {
          type: 'value',
          name: '市值(元)',
          position: 'right',
          offset: 60,
          axisLabel: {
            formatter: (value: number) => `¥${(value / 10000).toFixed(0)}万`,
          },
        },
      ],
      series: series,
      dataZoom: [
        {
          type: 'inside',
          start: 0,
          end: 100,
        },
        {
          show: true,
          type: 'slider',
          top: '90%',
          start: 0,
          end: 100,
        },
      ],
    };
  };

  // 计算总仓位统计指标
  const totalPositionStats = useMemo(() => {
    try {
      const filteredData = getFilteredData(totalPositionData);
      if (filteredData.length === 0) {
        return {
          avgPositionValue: 0,
          maxPositionValue: 0,
          minPositionValue: 0,
          avgPositionRatio: 0,
          avgStockCount: 0,
          maxStockCount: 0,
          minStockCount: 0,
        };
      }

      const values = filteredData.map((item) => item.totalValue).filter(v => isFinite(v));
      if (values.length === 0) {
        return {
          avgPositionValue: 0,
          maxPositionValue: 0,
          minPositionValue: 0,
          avgPositionRatio: 0,
          avgStockCount: 0,
          maxStockCount: 0,
          minStockCount: 0,
        };
      }

      const avgPositionValue = values.reduce((sum, v) => sum + v, 0) / values.length;
      const maxPositionValue = Math.max(...values, 0);
      const minPositionValue = Math.min(...values, 0);

      // 计算平均仓位率
      const ratios = filteredData.map((item) => {
        const dateStr = item.date;
        const profitItem = profitData.find((p) => {
          const pDate = String(p.date || p.gmt_create_time || p.gmt_create || '').substring(0, 8);
          return pDate === dateStr;
        });

        if (profitItem) {
          const totalValue = Number(
            profitItem.total_value ?? profitItem.total_profit ?? profitItem.strategy_profit ?? 0
          );
          if (totalValue > 0) {
            return (item.totalValue / totalValue) * 100;
          }
        }
        return 0;
      }).filter(r => isFinite(r));

      const avgPositionRatio = ratios.length > 0 
        ? ratios.reduce((sum, r) => sum + r, 0) / ratios.length 
        : 0;

      // 计算持仓股票数量统计
      const stockCounts = filteredData.map((item) => item.symbolCount).filter(c => isFinite(c));
      const avgStockCount = stockCounts.length > 0
        ? stockCounts.reduce((sum, c) => sum + c, 0) / stockCounts.length
        : 0;
      const maxStockCount = stockCounts.length > 0 ? Math.max(...stockCounts, 0) : 0;
      const minStockCount = stockCounts.length > 0 ? Math.min(...stockCounts, 0) : 0;

      return {
        avgPositionValue: isFinite(avgPositionValue) ? avgPositionValue : 0,
        maxPositionValue: isFinite(maxPositionValue) ? maxPositionValue : 0,
        minPositionValue: isFinite(minPositionValue) ? minPositionValue : 0,
        avgPositionRatio: isFinite(avgPositionRatio) ? avgPositionRatio : 0,
        avgStockCount: isFinite(avgStockCount) ? avgStockCount : 0,
        maxStockCount: isFinite(maxStockCount) ? maxStockCount : 0,
        minStockCount: isFinite(minStockCount) ? minStockCount : 0,
      };
    } catch (error) {
      console.error('计算总仓位统计失败:', error);
      return {
        avgPositionValue: 0,
        maxPositionValue: 0,
        minPositionValue: 0,
        avgPositionRatio: 0,
        avgStockCount: 0,
        maxStockCount: 0,
        minStockCount: 0,
      };
    }
  }, [totalPositionData, profitData, dateRange]);

  // 计算个股持仓统计指标
  const stockPositionStats = useMemo(() => {
    try {
      if (!selectedSymbol) {
        return {
          avgVolume: 0,
          maxVolume: 0,
          avgMarketValue: 0,
          maxMarketValue: 0,
        };
      }

      const symbolPositions = positionData.filter(
        (p) => (p.symbol || p.contract_code || p.code) === selectedSymbol
      );

      const filteredData = getFilteredData(symbolPositions);

      if (filteredData.length === 0) {
        return {
          avgVolume: 0,
          maxVolume: 0,
          avgMarketValue: 0,
          maxMarketValue: 0,
        };
      }

      const volumes = filteredData.map((item) => Number(item.volume || 0)).filter(v => isFinite(v));
      const marketValues = filteredData.map((item) => Number(item.market_value || 0)).filter(v => isFinite(v));

      if (volumes.length === 0 || marketValues.length === 0) {
        return {
          avgVolume: 0,
          maxVolume: 0,
          avgMarketValue: 0,
          maxMarketValue: 0,
        };
      }

      const avgVolume = volumes.reduce((sum, v) => sum + v, 0) / volumes.length;
      const maxVolume = Math.max(...volumes, 0);
      const avgMarketValue = marketValues.reduce((sum, v) => sum + v, 0) / marketValues.length;
      const maxMarketValue = Math.max(...marketValues, 0);

      return {
        avgVolume: isFinite(avgVolume) ? avgVolume : 0,
        maxVolume: isFinite(maxVolume) ? maxVolume : 0,
        avgMarketValue: isFinite(avgMarketValue) ? avgMarketValue : 0,
        maxMarketValue: isFinite(maxMarketValue) ? maxMarketValue : 0,
      };
    } catch (error) {
      console.error('计算个股持仓统计失败:', error);
      return {
        avgVolume: 0,
        maxVolume: 0,
        avgMarketValue: 0,
        maxMarketValue: 0,
      };
    }
  }, [selectedSymbol, positionData, dateRange]);

  return (
    <div style={{ padding: '24px' }}>
      <Card>
        <Title level={4}>
          <BarChartOutlined /> 仓位分析
        </Title>
        <div style={{ marginBottom: 24 }}>
          <Text type="secondary">
            分析总仓位与指数的关系，判断整体择时能力；分析个股仓位与K线的关系，判断个股择时能力。
          </Text>
        </div>

        {/* 日期范围筛选 */}
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={12}>
            <Space direction="vertical" style={{ width: '100%' }}>
              <Text strong>选择日期范围（可选）：</Text>
              <RangePicker
                style={{ width: '100%' }}
                format="YYYY-MM-DD"
                onChange={(dates) => {
                  if (dates && dates[0] && dates[1]) {
                    setDateRange([dates[0].format('YYYYMMDD'), dates[1].format('YYYYMMDD')]);
                  } else {
                    setDateRange(null);
                  }
                }}
              />
            </Space>
          </Col>
        </Row>

        {/* Tab切换：总仓位分析 vs 个股仓位分析 */}
        <Tabs defaultActiveKey="total" size="large">
          {/* 总仓位分析 */}
          <TabPane
            tab={
              <span>
                <LineChartOutlined /> 总仓位分析
              </span>
            }
            key="total"
          >
            {/* 统计指标 - 第一行 */}
            <Row gutter={16} style={{ marginBottom: 16 }}>
              <Col span={6}>
                <Card>
                  <Statistic
                    title="平均仓位价值"
                    value={totalPositionStats.avgPositionValue.toFixed(0)}
                    prefix="¥"
                    valueStyle={{ color: '#5470c6' }}
                  />
                </Card>
              </Col>
              <Col span={6}>
                <Card>
                  <Statistic
                    title="最大仓位价值"
                    value={totalPositionStats.maxPositionValue.toFixed(0)}
                    prefix="¥"
                    valueStyle={{ color: '#ff4d4f' }}
                  />
                </Card>
              </Col>
              <Col span={6}>
                <Card>
                  <Statistic
                    title="最小仓位价值"
                    value={totalPositionStats.minPositionValue.toFixed(0)}
                    prefix="¥"
                    valueStyle={{ color: '#52c41a' }}
                  />
                </Card>
              </Col>
              <Col span={6}>
                <Card>
                  <Statistic
                    title="平均仓位率"
                    value={totalPositionStats.avgPositionRatio.toFixed(2)}
                    suffix="%"
                    valueStyle={{ color: '#722ed1' }}
                  />
                </Card>
              </Col>
            </Row>

            {/* 统计指标 - 第二行：持仓数量统计 */}
            <Row gutter={16} style={{ marginBottom: 16 }}>
              <Col span={8}>
                <Card>
                  <Statistic
                    title="平均持仓股票数"
                    value={totalPositionStats.avgStockCount.toFixed(1)}
                    suffix="只"
                    valueStyle={{ color: '#1890ff' }}
                  />
                </Card>
              </Col>
              <Col span={8}>
                <Card>
                  <Statistic
                    title="最大持仓股票数"
                    value={totalPositionStats.maxStockCount}
                    suffix="只"
                    valueStyle={{ color: '#ff4d4f' }}
                  />
                </Card>
              </Col>
              <Col span={8}>
                <Card>
                  <Statistic
                    title="最小持仓股票数"
                    value={totalPositionStats.minStockCount}
                    suffix="只"
                    valueStyle={{ color: '#52c41a' }}
                  />
                </Card>
              </Col>
            </Row>

            {/* 控制栏 */}
            <div
              style={{
                marginBottom: 16,
                background: '#fafafa',
                padding: '12px',
                borderRadius: '4px',
              }}
            >
              <Space>
                <Text strong>显示：</Text>
                <Checkbox checked={showPosition} onChange={(e) => setShowPosition(e.target.checked)}>
                  仓位曲线
                </Checkbox>
                <Checkbox checked={showIndex} onChange={(e) => setShowIndex(e.target.checked)}>
                  基准指数
                </Checkbox>
                <Tooltip title="通过对比仓位变化与指数走势，可以判断策略的整体择时能力。理想情况下，仓位应在指数上涨前增加，在指数下跌前减少。">
                  <InfoCircleOutlined style={{ color: '#1890ff', cursor: 'pointer' }} />
                </Tooltip>
              </Space>
            </div>

            {/* 总仓位曲线图 */}
            <Card style={{ marginBottom: 24 }} title="总仓位价值与指数对比">
              {loading ? (
                <div style={{ textAlign: 'center', padding: '100px 0' }}>
                  <Spin size="large" tip="加载数据中..." />
                </div>
              ) : totalPositionData.length > 0 ? (
                <div style={{ width: '100%', minHeight: '600px' }}>
                  <ReactECharts
                    option={getTotalPositionChartOption()}
                    style={{ width: '100%', height: '600px' }}
                    notMerge={true}
                    lazyUpdate={true}
                  />
                </div>
              ) : (
                <Empty description="暂无仓位数据" />
              )}
            </Card>

            {/* 持仓数量与指数走势图 */}
            <Card 
              title={
                <span>
                  持仓股票数量与指数走势
                  <Tooltip 
                    title={
                      <div>
                        <div>• 通过对比持仓股票数量与指数走势，判断策略的分散度管理能力</div>
                        <div>• 理想情况：在指数上涨时增加持仓数量（捕捉机会），在指数下跌时减少持仓数量（控制风险）</div>
                        <div>• 也可能采取逆向策略：在指数下跌时加仓（抄底），在指数上涨时减仓（避险）</div>
                      </div>
                    }
                    placement="topLeft"
                  >
                    <InfoCircleOutlined style={{ marginLeft: 8, color: '#1890ff', cursor: 'pointer' }} />
                  </Tooltip>
                </span>
              }
            >
              {loading ? (
                <div style={{ textAlign: 'center', padding: '100px 0' }}>
                  <Spin size="large" tip="加载数据中..." />
                </div>
              ) : totalPositionData.length > 0 ? (
                <div style={{ width: '100%', minHeight: '500px' }}>
                  <ReactECharts
                    option={getStockCountIndexChartOption()}
                    style={{ width: '100%', height: '500px' }}
                    notMerge={true}
                    lazyUpdate={true}
                  />
                </div>
              ) : (
                <Empty description="暂无仓位数据" />
              )}
            </Card>
          </TabPane>

          {/* 个股仓位分析 */}
          <TabPane
            tab={
              <span>
                <StockOutlined /> 个股仓位分析
              </span>
            }
            key="stock"
          >
            {/* 选择器区域 */}
            <Row gutter={16} style={{ marginBottom: 24 }}>
              <Col span={8}>
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Text strong>选择股票：</Text>
                  <Select
                    style={{ width: '100%' }}
                    placeholder="请选择股票代码"
                    value={selectedSymbol || undefined}
                    onChange={setSelectedSymbol}
                    showSearch
                    filterOption={(input, option) =>
                      (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                    }
                    options={symbols.map((s) => ({ label: s, value: s }))}
                  />
                </Space>
              </Col>
            </Row>

            {!selectedSymbol ? (
              <Alert
                message="请选择股票"
                description="请在上方选择一个股票代码以查看其持仓曲线和K线分析"
                type="info"
                showIcon
              />
            ) : (
              <>
                {/* 统计指标 */}
                <Row gutter={16} style={{ marginBottom: 16 }}>
                  <Col span={6}>
                    <Card>
                      <Statistic
                        title="平均持仓量"
                        value={stockPositionStats.avgVolume.toFixed(0)}
                        suffix="股"
                        valueStyle={{ color: '#5470c6' }}
                      />
                    </Card>
                  </Col>
                  <Col span={6}>
                    <Card>
                      <Statistic
                        title="最大持仓量"
                        value={stockPositionStats.maxVolume.toFixed(0)}
                        suffix="股"
                        valueStyle={{ color: '#ff4d4f' }}
                      />
                    </Card>
                  </Col>
                  <Col span={6}>
                    <Card>
                      <Statistic
                        title="平均持仓市值"
                        value={stockPositionStats.avgMarketValue.toFixed(0)}
                        prefix="¥"
                        valueStyle={{ color: '#52c41a' }}
                      />
                    </Card>
                  </Col>
                  <Col span={6}>
                    <Card>
                      <Statistic
                        title="最大持仓市值"
                        value={stockPositionStats.maxMarketValue.toFixed(0)}
                        prefix="¥"
                        valueStyle={{ color: '#722ed1' }}
                      />
                    </Card>
                  </Col>
                </Row>

                {/* 控制栏 */}
                <div
                  style={{
                    marginBottom: 16,
                    background: '#fafafa',
                    padding: '12px',
                    borderRadius: '4px',
                  }}
                >
                  <Space>
                    <Text strong>显示：</Text>
                    <Checkbox
                      checked={showStockPosition}
                      onChange={(e) => setShowStockPosition(e.target.checked)}
                    >
                      持仓曲线
                    </Checkbox>
                    <Checkbox checked={showKLine} onChange={(e) => setShowKLine(e.target.checked)}>
                      K线图
                    </Checkbox>
                    <Tooltip title="通过对比个股持仓与K线走势，可以判断策略的个股择时能力。理想情况下，应在股价上涨前增加持仓，在股价下跌前减少持仓。">
                      <InfoCircleOutlined style={{ color: '#1890ff', cursor: 'pointer' }} />
                    </Tooltip>
                  </Space>
                </div>

                {/* 个股仓位曲线图 */}
                {loading ? (
                  <div style={{ textAlign: 'center', padding: '100px 0' }}>
                    <Spin size="large" tip="加载K线数据中..." />
                  </div>
                ) : selectedSymbol ? (
                  <div style={{ width: '100%', minHeight: '600px' }}>
                    <ReactECharts
                      option={getStockPositionChartOption()}
                      style={{ width: '100%', height: '600px' }}
                      notMerge={true}
                      lazyUpdate={true}
                    />
                  </div>
                ) : (
                  <Empty description="请选择股票以查看图表" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                )}
              </>
            )}
          </TabPane>
        </Tabs>
      </Card>
    </div>
  );
};

export default PositionAnalysis;

