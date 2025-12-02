import React, { useState, useEffect, useMemo } from 'react';
import {
  Card,
  Select,
  DatePicker,
  Row,
  Col,
  Statistic,
  Tag,
  Table,
  Space,
  Empty,
  Spin,
  Alert,
  Typography,
  Tooltip,
  Tabs,
  Badge,
} from 'antd';
import {
  ArrowUpOutlined,
  ArrowDownOutlined,
  TrophyOutlined,
  DollarOutlined,
  PercentageOutlined,
  SwapOutlined,
  RiseOutlined,
  ClockCircleOutlined,
  InfoCircleOutlined,
  StockOutlined,
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import type { TradeData, PositionData } from '@/types';
import { quotationApi } from '@/services/api';
import dayjs from 'dayjs';

const { RangePicker } = DatePicker;
const { Title, Text } = Typography;
const { TabPane } = Tabs;

interface TradeAnalysisProps {
  tradeData: TradeData[];
  positionData: PositionData[];
  backtestId?: string;
}

interface KLineData {
  date: string;
  open: number;
  close: number;
  low: number;
  high: number;
  volume: number;
}

const TradeAnalysis: React.FC<TradeAnalysisProps> = ({
  tradeData,
}) => {
  const [selectedSymbol, setSelectedSymbol] = useState<string>('');
  const [dateRange, setDateRange] = useState<[string, string] | null>(null);
  const [loading, setLoading] = useState(false);
  const [klineData, setKlineData] = useState<KLineData[]>([]);
  const [filteredTrades, setFilteredTrades] = useState<TradeData[]>([]);

  // 提取所有唯一的股票代码和名称
  const symbolNameMap = useMemo(() => {
    const map = new Map<string, string>();
    tradeData.forEach((t) => {
      const code = t.code;
      const name = t.contract_name || t.name || '';
      if (code && !map.has(code)) {
        map.set(code, name);
      }
    });
    return map;
  }, [tradeData]);

  const symbols = Array.from(symbolNameMap.keys()).sort();

  // 当选择的股票或日期范围变化时，过滤交易数据
  useEffect(() => {
    if (!selectedSymbol) {
      setFilteredTrades([]);
      return;
    }

    let filtered = tradeData.filter(t => t.code === selectedSymbol);
    
    if (dateRange) {
      filtered = filtered.filter(t => {
        const tradeDate = t.date;
        return tradeDate >= dateRange[0] && tradeDate <= dateRange[1];
      });
    }

    setFilteredTrades(filtered.sort((a, b) => a.date.localeCompare(b.date)));

    // 调用后端API获取K线数据
    fetchKLineData(selectedSymbol, dateRange);
  }, [selectedSymbol, dateRange, tradeData]);

  // 从后端API获取K线数据
  const fetchKLineData = async (symbol: string, range: [string, string] | null) => {
    if (!symbol) {
      setKlineData([]);
      return;
    }

    setLoading(true);
    
    try {
      const symbolTrades = tradeData.filter(t => t.code === symbol);
      
      if (symbolTrades.length === 0) {
        setKlineData([]);
        setLoading(false);
        return;
      }

      // 获取交易日期范围
      const dates = symbolTrades.map(t => t.date).sort();
      const startDate = range ? range[0] : dates[0];
      
      // 检查是否有未卖出的持仓
      const buyTrades = symbolTrades.filter(t => t.direction === 'buy');
      const sellTrades = symbolTrades.filter(t => t.direction === 'sell');
      const totalBuyAmount = buyTrades.reduce((sum, t) => sum + t.amount, 0);
      const totalSellAmount = sellTrades.reduce((sum, t) => sum + t.amount, 0);
      const hasUnclosedPosition = totalBuyAmount > totalSellAmount;
      
      // 如果用户指定了日期范围，使用用户指定的结束日期
      // 如果没有指定且有未平仓持仓，则加载到当前日期（或尽可能获取最新数据）
      let endDate: string;
      if (range) {
        endDate = range[1];
      } else if (hasUnclosedPosition) {
        // 有未平仓持仓，加载到当前日期（格式：YYYYMMDD）
        endDate = dayjs().format('YYYYMMDD');
      } else {
        // 没有未平仓持仓，使用最后一个交易日期
        endDate = dates[dates.length - 1];
      }
      
      // 调用API获取K线数据
      const apiData = await quotationApi.getStockKLineData(symbol, startDate, endDate);
      
      // 转换API数据格式为组件需要的格式
      const klineData: KLineData[] = apiData.map((item: any) => ({
        date: item.date || item.trade_date?.toString() || '',
        open: Number(item.open || 0),
        close: Number(item.close || 0),
        high: Number(item.high || 0),
        low: Number(item.low || 0),
        volume: Number(item.volume || 0),
      })).filter((item: KLineData) => item.date.length === 8); // 确保日期格式正确
      
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

  // 计算交易统计 - 包含8个核心指标
  const calculateStats = useMemo(() => {
    if (filteredTrades.length === 0) {
      return {
        totalTrades: 0,
        buyCount: 0,
        sellCount: 0,
        totalAmount: 0,
        winRate: 0,
        profitLossRatio: 0,
        totalProfit: 0,
        avgHoldDays: 0,
        tradePairs: [],
      };
    }

    const buyTrades = filteredTrades.filter(t => t.direction === 'buy');
    const sellTrades = filteredTrades.filter(t => t.direction === 'sell');
    
    // 计算总交易金额
    const totalAmount = filteredTrades.reduce((sum, t) => {
      const amount = parseFloat(t.cost || '0');
      return sum + amount;
    }, 0);

    // 买卖配对计算盈亏
    const tradePairs: Array<{
      buyDate: string;
      sellDate: string;
      buyPrice: number;
      sellPrice: number;
      amount: number;
      profit: number;
      holdDays: number;
      isSimulated?: boolean; // 标记是否为模拟清仓
    }> = [];

    // 简化配对逻辑：按时间顺序配对（FIFO）
    const buyQueue = [...buyTrades].sort((a, b) => a.date.localeCompare(b.date));
    const sellQueue = [...sellTrades].sort((a, b) => a.date.localeCompare(b.date));

    let buyIndex = 0;
    let sellIndex = 0;
    let remainingBuyAmount = 0;
    let currentBuyPrice = 0;
    let currentBuyDate = '';

    // 先处理已配对的买卖
    while (buyIndex < buyQueue.length && sellIndex < sellQueue.length) {
      const buy = buyQueue[buyIndex];
      const sell = sellQueue[sellIndex];

      if (remainingBuyAmount === 0) {
        // 新的买入
        remainingBuyAmount = buy.amount;
        currentBuyPrice = parseFloat(buy.price || '0');
        currentBuyDate = buy.date;
      }

      const sellAmount = sell.amount;
      const sellPrice = parseFloat(sell.price || '0');
      const sellDate = sell.date;

      const matchAmount = Math.min(remainingBuyAmount, sellAmount);
      const profit = (sellPrice - currentBuyPrice) * matchAmount;

      // 计算持仓天数
      const buyDay = dayjs(currentBuyDate, 'YYYYMMDD');
      const sellDay = dayjs(sellDate, 'YYYYMMDD');
      const holdDays = sellDay.diff(buyDay, 'day');

      tradePairs.push({
        buyDate: currentBuyDate,
        sellDate,
        buyPrice: currentBuyPrice,
        sellPrice,
        amount: matchAmount,
        profit,
        holdDays,
        isSimulated: false,
      });

      remainingBuyAmount -= matchAmount;

      if (remainingBuyAmount <= 0) {
        buyIndex++;
        remainingBuyAmount = 0;
      }

      if (matchAmount >= sellAmount) {
        sellIndex++;
      }
    }

    // 处理剩余的未配对买入（未卖出的持仓）
    // 收集所有未配对的买入记录
    const unclosedPositions: Array<{
      buyDate: string;
      buyPrice: number;
      amount: number;
    }> = [];

    // 处理当前正在处理的买入
    if (remainingBuyAmount > 0) {
      unclosedPositions.push({
        buyDate: currentBuyDate,
        buyPrice: currentBuyPrice,
        amount: remainingBuyAmount,
      });
      buyIndex++;
    }

    // 处理剩余的买入
    while (buyIndex < buyQueue.length) {
      const buy = buyQueue[buyIndex];
      unclosedPositions.push({
        buyDate: buy.date,
        buyPrice: parseFloat(buy.price || '0'),
        amount: buy.amount,
      });
      buyIndex++;
    }

    // 如果有未平仓持仓且K线数据可用，在最后一个交易日模拟清仓
    if (unclosedPositions.length > 0 && klineData.length > 0) {
      const lastKline = klineData[klineData.length - 1];
      const simulatedSellDate = lastKline.date;
      const simulatedSellPrice = lastKline.close;

      unclosedPositions.forEach(position => {
        const profit = (simulatedSellPrice - position.buyPrice) * position.amount;
        const buyDay = dayjs(position.buyDate, 'YYYYMMDD');
        const sellDay = dayjs(simulatedSellDate, 'YYYYMMDD');
        const holdDays = sellDay.diff(buyDay, 'day');

        tradePairs.push({
          buyDate: position.buyDate,
          sellDate: simulatedSellDate,
          buyPrice: position.buyPrice,
          sellPrice: simulatedSellPrice,
          amount: position.amount,
          profit,
          holdDays,
          isSimulated: true, // 标记为模拟清仓
        });
      });
    }

    // 计算各项指标
    const winTrades = tradePairs.filter(p => p.profit > 0);
    const lossTrades = tradePairs.filter(p => p.profit < 0);
    
    // 1. 胜率
    const winRate = tradePairs.length > 0 ? (winTrades.length / tradePairs.length) * 100 : 0;

    // 2. 总盈亏
    const totalProfit = tradePairs.reduce((sum, p) => sum + p.profit, 0);

    // 3. 盈亏比
    const avgWin = winTrades.length > 0 
      ? winTrades.reduce((sum, p) => sum + p.profit, 0) / winTrades.length 
      : 0;
    const avgLoss = lossTrades.length > 0 
      ? Math.abs(lossTrades.reduce((sum, p) => sum + p.profit, 0) / lossTrades.length)
      : 0;
    const profitLossRatio = avgLoss > 0 ? avgWin / avgLoss : 0;

    // 4. 平均持仓天数
    const avgHoldDays = tradePairs.length > 0
      ? tradePairs.reduce((sum, p) => sum + p.holdDays, 0) / tradePairs.length
      : 0;

    return {
      totalTrades: filteredTrades.length,
      buyCount: buyTrades.length,
      sellCount: sellTrades.length,
      totalAmount,
      winRate,
      profitLossRatio,
      totalProfit,
      avgHoldDays,
      tradePairs, // 保存配对数据供后续使用
    };
  }, [filteredTrades, klineData]);

  const stats = calculateStats;

  // 计算所有股票的统计数据（用于对比视图）
  const allSymbolsStats = useMemo(() => {
    const symbolStatsMap: { [key: string]: any } = {};

    symbols.forEach(symbol => {
      const symbolTrades = tradeData.filter(t => t.code === symbol);
      const buyTrades = symbolTrades.filter(t => t.direction === 'buy');
      const sellTrades = symbolTrades.filter(t => t.direction === 'sell');

      // 计算总交易金额
      const totalAmount = symbolTrades.reduce((sum, t) => {
        const amount = parseFloat(t.cost || '0');
        return sum + amount;
      }, 0);

      // 买卖配对计算盈亏
      const tradePairs: Array<{
        buyPrice: number;
        sellPrice: number;
        amount: number;
        profit: number;
        holdDays: number;
      }> = [];

      const buyQueue = [...buyTrades].sort((a, b) => a.date.localeCompare(b.date));
      const sellQueue = [...sellTrades].sort((a, b) => a.date.localeCompare(b.date));

      let buyIndex = 0;
      let sellIndex = 0;
      let remainingBuyAmount = 0;
      let currentBuyPrice = 0;
      let currentBuyDate = '';

      while (buyIndex < buyQueue.length && sellIndex < sellQueue.length) {
        const buy = buyQueue[buyIndex];
        const sell = sellQueue[sellIndex];

        if (remainingBuyAmount === 0) {
          remainingBuyAmount = buy.amount;
          currentBuyPrice = parseFloat(buy.price || '0');
          currentBuyDate = buy.date;
        }

        const sellAmount = sell.amount;
        const sellPrice = parseFloat(sell.price || '0');
        const sellDate = sell.date;

        const matchAmount = Math.min(remainingBuyAmount, sellAmount);
        const profit = (sellPrice - currentBuyPrice) * matchAmount;

        const buyDay = dayjs(currentBuyDate, 'YYYYMMDD');
        const sellDay = dayjs(sellDate, 'YYYYMMDD');
        const holdDays = sellDay.diff(buyDay, 'day');

        tradePairs.push({
          buyPrice: currentBuyPrice,
          sellPrice,
          amount: matchAmount,
          profit,
          holdDays,
        });

        remainingBuyAmount -= matchAmount;

        if (remainingBuyAmount <= 0) {
          buyIndex++;
          remainingBuyAmount = 0;
        }

        if (matchAmount >= sellAmount) {
          sellIndex++;
        }
      }

      // 计算指标
      const winTrades = tradePairs.filter(p => p.profit > 0);
      const lossTrades = tradePairs.filter(p => p.profit < 0);
      const winRate = tradePairs.length > 0 ? (winTrades.length / tradePairs.length) * 100 : 0;
      const totalProfit = tradePairs.reduce((sum, p) => sum + p.profit, 0);
      const avgWin = winTrades.length > 0 
        ? winTrades.reduce((sum, p) => sum + p.profit, 0) / winTrades.length 
        : 0;
      const avgLoss = lossTrades.length > 0 
        ? Math.abs(lossTrades.reduce((sum, p) => sum + p.profit, 0) / lossTrades.length)
        : 0;
      const profitLossRatio = avgLoss > 0 ? avgWin / avgLoss : 0;
      const avgHoldDays = tradePairs.length > 0
        ? tradePairs.reduce((sum, p) => sum + p.holdDays, 0) / tradePairs.length
        : 0;

      symbolStatsMap[symbol] = {
        symbol,
        contract_name: symbolNameMap.get(symbol) || '',
        totalTrades: symbolTrades.length,
        buyCount: buyTrades.length,
        sellCount: sellTrades.length,
        totalAmount,
        winRate,
        profitLossRatio,
        totalProfit,
        avgHoldDays,
        tradePairs: tradePairs.length,
      };
    });

    return Object.values(symbolStatsMap);
  }, [tradeData, symbols]);

  // 生成K线图配置
  const getKLineOption = () => {
    if (klineData.length === 0) {
      return {};
    }

    const dates = klineData.map(d => {
      const date = d.date;
      return `${date.substring(0, 4)}-${date.substring(4, 6)}-${date.substring(6, 8)}`;
    });

    const values = klineData.map(d => [d.open, d.close, d.low, d.high]);

    // 准备买卖点数据
    const buyPoints: any[] = [];
    const sellPoints: any[] = [];
    const simulatedSellPoints: any[] = []; // 模拟清仓点

    // 添加实际交易点（使用成交价，与下方交易记录表价格保持一致）
    filteredTrades.forEach(trade => {
      const tradeDate = trade.date;
      if (!tradeDate || tradeDate.length < 8) return;

      const formattedDate = `${tradeDate.substring(0, 4)}-${tradeDate.substring(4, 6)}-${tradeDate.substring(6, 8)}`;
      const dateIndex = dates.indexOf(formattedDate);
      if (dateIndex === -1) return;

      const kline = klineData[dateIndex];
      const price = parseFloat(trade.price || '0');

      if (trade.direction === 'buy') {
        // 买入点：优先使用成交价，缺失或为 0 时回退到当日K线最低价
        const yPosition = (price && !Number.isNaN(price)) ? price : (kline ? kline.low : 0);
        buyPoints.push({
          xAxis: dateIndex,
          yAxis: yPosition,
          value: trade.amount,
        });
      } else if (trade.direction === 'sell') {
        // 卖出点：优先使用成交价，缺失或为 0 时回退到当日K线最高价
        const yPosition = (price && !Number.isNaN(price)) ? price : (kline ? kline.high : 0);
        sellPoints.push({
          xAxis: dateIndex,
          yAxis: yPosition,
          value: trade.amount,
        });
      }
    });

    // 添加模拟清仓点：使用配对结果中的卖出价格
    if (stats.tradePairs) {
      stats.tradePairs.forEach((pair: any) => {
        if (!pair.isSimulated) return;

        const sellDate = pair.sellDate;
        if (!sellDate || sellDate.length < 8) return;

        const formattedDate = `${sellDate.substring(0, 4)}-${sellDate.substring(4, 6)}-${sellDate.substring(6, 8)}`;
        const dateIndex = dates.indexOf(formattedDate);
        if (dateIndex === -1) return;

        const kline = klineData[dateIndex];
        const price = pair.sellPrice;
        const yPosition = (price && !Number.isNaN(price)) ? price : (kline ? kline.close : 0);

        simulatedSellPoints.push({
          xAxis: dateIndex,
          yAxis: yPosition,
          value: pair.amount,
        });
      });
    }

    // 计算所有有交易信号的日期索引，用于绘制垂直辅助线
    const tradeXIndexes = Array.from(
      new Set([
        ...buyPoints.map(p => p.xAxis),
        ...sellPoints.map(p => p.xAxis),
        ...simulatedSellPoints.map(p => p.xAxis),
      ])
    ).sort((a, b) => a - b);

    return {
      animation: true,
      title: {
        text: `${selectedSymbol} ${symbolNameMap.get(selectedSymbol) || ''} K线图与交易点`,
        left: 'center',
      },
      legend: {
        data: simulatedSellPoints.length > 0
          ? ['K线', '买入', '卖出', '模拟清仓']
          : ['K线', '买入', '卖出'],
        top: 30,
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
            if (param.seriesName === 'K线') {
              const kline = param.value;
              result += `开盘: ${kline[1]}<br/>`;
              result += `收盘: ${kline[2]}<br/>`;
              result += `最低: ${kline[3]}<br/>`;
              result += `最高: ${kline[4]}<br/>`;
            } else if (param.seriesName === '买入') {
              result += `<span style="color: #ef5350;">▲</span> 买入: ¥${param.value[1].toFixed(2)}<br/>`;
            } else if (param.seriesName === '卖出') {
              result += `<span style="color: #26a69a;">▼</span> 卖出: ¥${param.value[1].toFixed(2)}<br/>`;
            } else if (param.seriesName === '模拟清仓') {
              result += `<span style="color: #ff9800;">▼</span> 模拟清仓: ¥${param.value[1].toFixed(2)}<br/>`;
            }
          });

          return result;
        },
      },
      grid: {
        left: '10%',
        right: '10%',
        bottom: '15%',
      },
      xAxis: {
        type: 'category',
        data: dates,
        scale: true,
        boundaryGap: true,
        axisLine: { onZero: false },
        splitLine: { show: false },
        min: 'dataMin',
        max: 'dataMax',
      },
      yAxis: {
        scale: true,
        splitArea: {
          show: true,
        },
      },
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
      series: [
        // K线
        {
          name: 'K线',
          type: 'candlestick',
          data: values,
          itemStyle: {
            color: '#ef5350', // 红涨
            color0: '#26a69a', // 绿跌
            borderColor: '#ef5350',
            borderColor0: '#26a69a',
          },
        },
        // 交易日垂直虚线（辅助线，不参与 tooltip）
        ...(tradeXIndexes.length > 0
          ? [{
              name: '交易日',
              type: 'line',
              data: [],
              xAxisIndex: 0,
              yAxisIndex: 0,
              symbol: 'none',
              lineStyle: { opacity: 0 },
              tooltip: { show: false },
              markLine: {
                symbol: ['none', 'none'],
                silent: true,
                lineStyle: {
                  type: 'dashed',
                  color: '#999',
                  opacity: 0.4,
                  width: 1,
                },
                data: tradeXIndexes.map(idx => ({ xAxis: dates[idx] })),
              },
              z: 6,
            }]
          : []),
        // 买入点散点图
        {
          name: '买入',
          type: 'scatter',
          symbol: 'triangle',
          symbolSize: 12,
          symbolRotate: 0,
          data: buyPoints.map(p => [p.xAxis, p.yAxis]),
          itemStyle: {
            color: '#ef5350',
          },
          label: {
            show: true,
            position: 'bottom',
            formatter: '买',
            color: '#ef5350',
            fontSize: 11,
            fontWeight: 'bold',
            offset: [0, 5],
          },
          z: 10,
        },
        // 卖出点散点图
        {
          name: '卖出',
          type: 'scatter',
          symbol: 'triangle',
          symbolSize: 12,
          symbolRotate: 180,
          data: sellPoints.map(p => [p.xAxis, p.yAxis]),
          itemStyle: {
            color: '#26a69a',
          },
          label: {
            show: true,
            position: 'top',
            formatter: '卖',
            color: '#26a69a',
            fontSize: 11,
            fontWeight: 'bold',
            offset: [0, -5],
          },
          z: 10,
        },
        // 模拟清仓点散点图
        ...(simulatedSellPoints.length > 0
          ? [{
            name: '模拟清仓',
            type: 'scatter',
            symbol: 'diamond',
            symbolSize: 14,
            symbolRotate: 0,
            data: simulatedSellPoints.map(p => [p.xAxis, p.yAxis]),
            itemStyle: {
              color: '#ff9800',
              borderColor: '#ff9800',
              borderWidth: 2,
            },
            label: {
              show: true,
              position: 'top',
              formatter: '模拟',
              color: '#ff9800',
              fontSize: 10,
              fontWeight: 'bold',
              offset: [0, -5],
            },
            z: 11,
          }]
          : []),
      ],
    };
  };

  // 股票对比表格列定义
  const comparisonColumns = [
    {
      title: '股票代码',
      dataIndex: 'symbol',
      key: 'symbol',
      width: 120,
      align: 'center' as const,
      fixed: 'left' as const,
      render: (symbol: string) => <Text strong>{symbol}</Text>,
    },
    {
      title: '证券名称',
      dataIndex: 'contract_name',
      key: 'contract_name',
      width: 120,
      align: 'center' as const,
      render: (contract_name: string, record: any) => {
        const name = symbolNameMap.get(record.symbol) || contract_name || '-';
        return <Text>{name}</Text>;
      },
    },
    {
      title: '交易对数',
      dataIndex: 'tradePairs',
      key: 'tradePairs',
      width: 100,
      align: 'center' as const,
      sorter: (a: any, b: any) => a.tradePairs - b.tradePairs,
    },
    {
      title: '总交易次数',
      dataIndex: 'totalTrades',
      key: 'totalTrades',
      width: 110,
      align: 'center' as const,
      sorter: (a: any, b: any) => a.totalTrades - b.totalTrades,
    },
    {
      title: '胜率',
      dataIndex: 'winRate',
      key: 'winRate',
      width: 100,
      align: 'center' as const,
      sorter: (a: any, b: any) => a.winRate - b.winRate,
      render: (winRate: number) => (
        <Text style={{ color: winRate >= 50 ? '#cf1322' : '#3f8600', fontWeight: 'bold' }}>
          {winRate.toFixed(2)}%
        </Text>
      ),
    },
    {
      title: '盈亏比',
      dataIndex: 'profitLossRatio',
      key: 'profitLossRatio',
      width: 100,
      align: 'center' as const,
      sorter: (a: any, b: any) => a.profitLossRatio - b.profitLossRatio,
      render: (ratio: number) => (
        <Text style={{ color: ratio >= 1 ? '#cf1322' : '#3f8600', fontWeight: 'bold' }}>
          {ratio.toFixed(2)}
        </Text>
      ),
    },
    {
      title: '总盈亏',
      dataIndex: 'totalProfit',
      key: 'totalProfit',
      width: 120,
      align: 'center' as const,
      sorter: (a: any, b: any) => a.totalProfit - b.totalProfit,
      render: (profit: number) => (
        <Text style={{ color: profit >= 0 ? '#cf1322' : '#3f8600', fontWeight: 'bold' }}>
          {profit >= 0 ? '+' : ''}¥{profit.toFixed(2)}
        </Text>
      ),
    },
    {
      title: '平均持仓天数',
      dataIndex: 'avgHoldDays',
      key: 'avgHoldDays',
      width: 130,
      align: 'center' as const,
      sorter: (a: any, b: any) => a.avgHoldDays - b.avgHoldDays,
      render: (days: number) => `${days.toFixed(1)}天`,
    },
    {
      title: '总交易金额',
      dataIndex: 'totalAmount',
      key: 'totalAmount',
      width: 140,
      align: 'center' as const,
      sorter: (a: any, b: any) => a.totalAmount - b.totalAmount,
      render: (amount: number) => `¥${amount.toLocaleString()}`,
    },
  ];

  // 交易记录表格列
  const tradeColumns = [
    {
      title: '日期',
      dataIndex: 'date',
      key: 'date',
      width: 110,
      align: 'center' as const,
      render: (date: string) => {
        if (date.length === 8) {
          return `${date.substring(0, 4)}-${date.substring(4, 6)}-${date.substring(6, 8)}`;
        }
        return date;
      },
    },
    {
      title: '方向',
      dataIndex: 'direction',
      key: 'direction',
      width: 80,
      align: 'center' as const,
      render: (direction: string) => (
        <Tag color={direction === 'buy' ? '#ff4d4f' : '#52c41a'} icon={direction === 'buy' ? <ArrowUpOutlined /> : <ArrowDownOutlined />}>
          {direction === 'buy' ? '买入' : '卖出'}
        </Tag>
      ),
    },
    {
      title: '价格',
      dataIndex: 'price',
      key: 'price',
      width: 100,
      align: 'center' as const,
      render: (price: string) => `¥${parseFloat(price).toFixed(2)}`,
    },
    {
      title: '数量',
      dataIndex: 'amount',
      key: 'amount',
      width: 100,
      align: 'center' as const,
      render: (amount: number) => amount.toLocaleString(),
    },
    {
      title: '金额',
      dataIndex: 'cost',
      key: 'cost',
      width: 120,
      align: 'center' as const,
      render: (cost: string) => `¥${parseFloat(cost || '0').toLocaleString()}`,
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      <Card>
        <Title level={4}>📈 交易分析 - K线图与买卖点</Title>
        <div style={{ marginBottom: 24 }}>
          <Text type="secondary">
            分析单个股票的完整交易历史，或对比所有股票的交易表现。使用FIFO（先进先出）算法配对买卖交易。
          </Text>
        </div>

        {/* Tab切换：单股票分析 vs 全部股票对比 */}
        <Tabs defaultActiveKey="single" size="large">
          <TabPane
            tab={
              <span>
                <StockOutlined /> 单股票分析
              </span>
            }
            key="single"
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
                options={symbols.map(s => {
                  const name = symbolNameMap.get(s);
                  const label = name ? `${name} (${s})` : s;
                  return { label, value: s };
                })}
              />
            </Space>
          </Col>
          <Col span={12}>
            <Space direction="vertical" style={{ width: '100%' }}>
              <Text strong>选择日期范围（可选）：</Text>
              <RangePicker
                style={{ width: '100%' }}
                format="YYYY-MM-DD"
                onChange={(dates) => {
                  if (dates && dates[0] && dates[1]) {
                    setDateRange([
                      dates[0].format('YYYYMMDD'),
                      dates[1].format('YYYYMMDD'),
                    ]);
                  } else {
                    setDateRange(null);
                  }
                }}
              />
            </Space>
          </Col>
        </Row>

        {!selectedSymbol ? (
          <Alert
            message="请选择股票"
            description="请在上方选择一个股票以查看其K线图和交易点分析"
            type="info"
            showIcon
          />
        ) : (
          <>
            {/* 统计信息 - 8个核心指标 */}
            {/* 第一行：基础交易指标 */}
            <Row gutter={16} style={{ marginBottom: 16 }}>
              <Col span={6}>
                <Card>
                  <Statistic
                    title="总交易次数"
                    value={stats.totalTrades}
                    prefix={<TrophyOutlined />}
                  />
                </Card>
              </Col>
              <Col span={6}>
                <Card>
                  <Statistic
                    title="买入次数"
                    value={stats.buyCount}
                    valueStyle={{ color: '#ff4d4f' }}
                    prefix={<ArrowUpOutlined />}
                  />
                </Card>
              </Col>
              <Col span={6}>
                <Card>
                  <Statistic
                    title="卖出次数"
                    value={stats.sellCount}
                    valueStyle={{ color: '#52c41a' }}
                    prefix={<ArrowDownOutlined />}
                  />
                </Card>
              </Col>
              <Col span={6}>
                <Card>
                  <Statistic
                    title="总交易金额"
                    value={stats.totalAmount.toFixed(2)}
                    precision={2}
                    prefix={<DollarOutlined />}
                    suffix="元"
                  />
                </Card>
              </Col>
            </Row>

            {/* 第二行：核心绩效指标 */}
            <Row gutter={16} style={{ marginBottom: 16 }}>
              <Col span={6}>
                <Card>
                  <Statistic
                    title="胜率"
                    value={stats.winRate.toFixed(2)}
                    precision={2}
                    suffix="%"
                    prefix={<PercentageOutlined />}
                    valueStyle={{ 
                      color: stats.winRate >= 50 ? '#cf1322' : '#3f8600',
                      fontWeight: 'bold',
                    }}
                  />
                </Card>
              </Col>
              <Col span={6}>
                <Card>
                  <Statistic
                    title="盈亏比"
                    value={stats.profitLossRatio.toFixed(2)}
                    precision={2}
                    prefix={<SwapOutlined />}
                    valueStyle={{ 
                      color: stats.profitLossRatio >= 1 ? '#cf1322' : '#3f8600',
                      fontWeight: 'bold',
                    }}
                  />
                </Card>
              </Col>
              <Col span={6}>
                <Card>
                  <Statistic
                    title="总盈亏"
                    value={stats.totalProfit.toFixed(2)}
                    precision={2}
                    prefix={<RiseOutlined />}
                    suffix="元"
                    valueStyle={{ 
                      color: stats.totalProfit >= 0 ? '#cf1322' : '#3f8600',
                      fontWeight: 'bold',
                    }}
                  />
                </Card>
              </Col>
              <Col span={6}>
                <Card>
                  <Statistic
                    title="平均持仓天数"
                    value={stats.avgHoldDays.toFixed(1)}
                    precision={1}
                    suffix="天"
                    prefix={<ClockCircleOutlined />}
                  />
                </Card>
              </Col>
            </Row>

            {/* 指标说明 - 小提示 */}
            <div style={{ marginBottom: 24, textAlign: 'right' }}>
              <Tooltip
                title={
                  <div>
                    <div><strong>胜率</strong>：盈利交易次数 ÷ 总交易对数 × 100%（≥50%为良好）</div>
                    <div><strong>盈亏比</strong>：平均盈利 ÷ 平均亏损（≥1为良好，≥2为优秀）</div>
                    <div><strong>总盈亏</strong>：所有交易配对后的累计盈亏金额</div>
                    <div><strong>平均持仓天数</strong>：从买入到卖出的平均持有时间</div>
                  </div>
                }
                placement="bottomRight"
              >
                <Text type="secondary" style={{ cursor: 'pointer' }}>
                  <InfoCircleOutlined /> 指标说明
                </Text>
              </Tooltip>
            </div>

            {/* K线图 */}
            <Card 
              style={{ marginBottom: 24 }} 
              title={
                <span>
                  K线图与交易点
                  <Tooltip
                    title={
                      <div>
                        <div>• 红色向上三角形▲标注买入点（定位在K线最低价）</div>
                        <div>• 绿色向下三角形▼标注卖出点（定位在K线最高价）</div>
                        <div>• K线采用A股配色：红涨绿跌</div>
                        <div>• 可以使用鼠标滚轮或拖动底部滑块缩放</div>
                        <div>• 点击图例可以单独显示/隐藏买入点或卖出点</div>
                      </div>
                    }
                    placement="bottomLeft"
                  >
                    <InfoCircleOutlined style={{ marginLeft: 8, color: '#1890ff', cursor: 'pointer' }} />
                  </Tooltip>
                </span>
              }
            >
              {loading ? (
                <div style={{ textAlign: 'center', padding: '100px 0' }}>
                  <Spin size="large" tip="加载K线数据中..." />
                </div>
              ) : klineData.length > 0 ? (
                <ReactECharts
                  option={getKLineOption()}
                  style={{ height: '500px' }}
                  notMerge={true}
                  lazyUpdate={true}
                />
              ) : (
                <Empty description="暂无K线数据" />
              )}
            </Card>

            {/* 交易记录表格 */}
            <Card title={`交易记录 (${filteredTrades.length}笔)`}>
              {filteredTrades.length > 0 ? (
                <Table
                  columns={tradeColumns}
                  dataSource={filteredTrades}
                  pagination={{
                    pageSize: 10,
                    showTotal: (total) => `共 ${total} 笔交易`,
                    showSizeChanger: true,
                  }}
                  size="small"
                  rowKey={(record, index) => `${record.date}_${index}`}
                />
              ) : (
                <Empty description="暂无交易记录" />
              )}
            </Card>
          </>
        )}
          </TabPane>

          {/* 全部股票对比视图 */}
          <TabPane
            tab={
              <span>
                <Badge count={symbols.length} showZero>
                  <SwapOutlined /> 全部股票对比
                </Badge>
              </span>
            }
            key="comparison"
          >
            <div style={{ marginBottom: 16 }}>
              <Text type="secondary">
                对比所有股票的交易表现，快速找出表现最优的股票。点击列标题可排序。
              </Text>
            </div>

            {allSymbolsStats.length > 0 ? (
              <>
                {/* 总体统计 */}
                <Row gutter={16} style={{ marginBottom: 24 }}>
                  <Col span={6}>
                    <Card>
                      <Statistic
                        title="总股票数"
                        value={symbols.length}
                        prefix={<TrophyOutlined />}
                      />
                    </Card>
                  </Col>
                  <Col span={6}>
                    <Card>
                      <Statistic
                        title="总盈亏"
                        value={allSymbolsStats.reduce((sum, s) => sum + s.totalProfit, 0).toFixed(2)}
                        precision={2}
                        prefix={<RiseOutlined />}
                        suffix="元"
                        valueStyle={{
                          color: allSymbolsStats.reduce((sum, s) => sum + s.totalProfit, 0) >= 0 ? '#cf1322' : '#3f8600',
                          fontWeight: 'bold',
                        }}
                      />
                    </Card>
                  </Col>
                  <Col span={6}>
                    <Card>
                      <Statistic
                        title="平均胜率"
                        value={(allSymbolsStats.reduce((sum, s) => sum + s.winRate, 0) / allSymbolsStats.length).toFixed(2)}
                        precision={2}
                        suffix="%"
                        prefix={<PercentageOutlined />}
                      />
                    </Card>
                  </Col>
                  <Col span={6}>
                    <Card>
                      <Statistic
                        title="平均盈亏比"
                        value={(allSymbolsStats.reduce((sum, s) => sum + s.profitLossRatio, 0) / allSymbolsStats.length).toFixed(2)}
                        precision={2}
                        prefix={<SwapOutlined />}
                      />
                    </Card>
                  </Col>
                </Row>

                {/* 股票对比表格 */}
                <Card title="股票交易对比表">
                  <Table
                    columns={comparisonColumns}
                    dataSource={allSymbolsStats}
                    pagination={{
                      pageSize: 20,
                      showTotal: (total) => `共 ${total} 只股票`,
                      showSizeChanger: true,
                    }}
                    size="small"
                    rowKey="symbol"
                    scroll={{ x: 1200 }}
                  />
                </Card>
              </>
            ) : (
              <Empty description="暂无交易数据" />
            )}
          </TabPane>
        </Tabs>
      </Card>
    </div>
  );
};

export default TradeAnalysis;

