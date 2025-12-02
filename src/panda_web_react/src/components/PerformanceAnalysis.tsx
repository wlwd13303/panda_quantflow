import React, { useState, useEffect, useMemo } from 'react';
import {
  Card,
  Table,
  Statistic,
  Row,
  Col,
  Spin,
  Empty,
  Typography,
  Alert,
  Tooltip,
  Tag,
} from 'antd';
import {
  ClockCircleOutlined,
  ThunderboltOutlined,
  InfoCircleOutlined,
  RocketOutlined,
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import { backtestApi } from '@/services/api';

const { Title, Text } = Typography;

interface PerformanceAnalysisProps {
  backtestId?: string;
}

interface TradingDayPerformance {
  date: string;
  duration: number; // 运行时间（秒）
  logCount: number; // 日志条数
  startTime: string; // 开始时间
  endTime: string; // 结束时间
}

const PerformanceAnalysis: React.FC<PerformanceAnalysisProps> = ({
  backtestId,
}) => {
  const [loading, setLoading] = useState(false);
  const [performanceData, setPerformanceData] = useState<TradingDayPerformance[]>([]);

  // 获取日志数据并计算性能指标
  useEffect(() => {
    const fetchPerformanceData = async () => {
      if (!backtestId) return;

      setLoading(true);
      try {
        // 获取所有日志数据
        const logs = await backtestApi.getLogs(backtestId, undefined, 10000);
        
        if (!logs || !logs.items || logs.items.length === 0) {
          setPerformanceData([]);
          setLoading(false);
          return;
        }

        // 按交易日分组（使用 exhibit_time 字段）
        const dayMap = new Map<string, any[]>();
        
        logs.items.forEach((log: any) => {
          // 获取交易时间（exhibit_time），转换为日期
          const exhibitTime = log.exhibit_time;
          if (!exhibitTime) return;
          
          // 将 ISO 时间字符串转换为日期（YYYYMMDD）
          const date = new Date(exhibitTime);
          if (isNaN(date.getTime())) return;
          
          const dateStr = `${date.getFullYear()}${String(date.getMonth() + 1).padStart(2, '0')}${String(date.getDate()).padStart(2, '0')}`;
          
          if (!dayMap.has(dateStr)) {
            dayMap.set(dateStr, []);
          }
          dayMap.get(dateStr)!.push(log);
        });

        // 计算每个交易日的性能指标
        const perfData: TradingDayPerformance[] = [];
        
        dayMap.forEach((logs, date) => {
          if (logs.length === 0) return;
          
          // 按 insert_time 排序
          logs.sort((a, b) => {
            const timeA = new Date(a.insert_time).getTime();
            const timeB = new Date(b.insert_time).getTime();
            return timeA - timeB;
          });
          
          const firstLog = logs[0];
          const lastLog = logs[logs.length - 1];
          
          const startTime = new Date(firstLog.insert_time);
          const endTime = new Date(lastLog.insert_time);
          
          // 计算时间差（秒）
          const duration = (endTime.getTime() - startTime.getTime()) / 1000;
          
          perfData.push({
            date,
            duration: Math.max(duration, 0.001), // 避免为0
            logCount: logs.length,
            startTime: firstLog.insert_time,
            endTime: lastLog.insert_time,
          });
        });

        // 按日期排序
        perfData.sort((a, b) => a.date.localeCompare(b.date));
        
        setPerformanceData(perfData);
      } catch (error) {
        console.error('获取性能数据失败:', error);
        setPerformanceData([]);
      } finally {
        setLoading(false);
      }
    };

    fetchPerformanceData();
  }, [backtestId]);

  // 计算统计指标
  const statistics = useMemo(() => {
    if (performanceData.length === 0) {
      return {
        avgDuration: 0,
        maxDuration: 0,
        minDuration: 0,
        totalDays: 0,
        totalTime: 0,
        fastestDay: '-',
        slowestDay: '-',
      };
    }

    const durations = performanceData.map(d => d.duration);
    const avgDuration = durations.reduce((sum, d) => sum + d, 0) / durations.length;
    const maxDuration = Math.max(...durations);
    const minDuration = Math.min(...durations);
    const totalTime = durations.reduce((sum, d) => sum + d, 0);
    
    const fastestDay = performanceData.find(d => d.duration === minDuration);
    const slowestDay = performanceData.find(d => d.duration === maxDuration);

    return {
      avgDuration,
      maxDuration,
      minDuration,
      totalDays: performanceData.length,
      totalTime,
      fastestDay: fastestDay ? fastestDay.date : '-',
      slowestDay: slowestDay ? slowestDay.date : '-',
    };
  }, [performanceData]);

  // 生成性能趋势图配置
  const getPerformanceChartOption = () => {
    if (performanceData.length === 0) {
      return {};
    }

    const dates = performanceData.map((item) => {
      const dateStr = item.date;
      return `${dateStr.substring(0, 4)}-${dateStr.substring(4, 6)}-${dateStr.substring(6, 8)}`;
    });

    const durations = performanceData.map((item) => item.duration.toFixed(3));

    return {
      title: {
        text: '每日策略运行时间趋势',
        left: 'center',
        top: 10,
        textStyle: {
          fontSize: 16,
          fontWeight: 'bold',
          color: '#333',
        },
      },
      tooltip: {
        trigger: 'axis',
        formatter: (params: any) => {
          if (!params || params.length === 0) return '';
          const param = params[0];
          return `${param.name}<br/>${param.marker} 运行时间: ${param.value}秒`;
        },
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
        data: dates,
        axisLabel: {
          rotate: 30,
          interval: Math.floor(dates.length / 10),
        },
      },
      yAxis: {
        type: 'value',
        name: '运行时间(秒)',
        axisLabel: {
          formatter: (value: number) => `${value}s`,
        },
      },
      series: [
        {
          name: '运行时间',
          type: 'line',
          data: durations,
          smooth: true,
          lineStyle: { color: '#5470c6', width: 2 },
          areaStyle: {
            color: {
              type: 'linear',
              x: 0,
              y: 0,
              x2: 0,
              y2: 1,
              colorStops: [
                { offset: 0, color: 'rgba(84, 112, 198, 0.3)' },
                { offset: 1, color: 'rgba(84, 112, 198, 0.05)' },
              ],
            },
          },
          markLine: {
            data: [
              {
                type: 'average',
                name: '平均值',
                lineStyle: { color: '#fac858', type: 'dashed' },
                label: { formatter: '平均: {c}s' },
              },
            ],
          },
          markPoint: {
            data: [
              { type: 'max', name: '最大值' },
              { type: 'min', name: '最小值' },
            ],
          },
        },
      ],
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

  // 表格列配置
  const columns = [
    {
      title: '交易日期',
      dataIndex: 'date',
      key: 'date',
      width: 120,
      align: 'center' as const,
      render: (date: string) => {
        return `${date.substring(0, 4)}-${date.substring(4, 6)}-${date.substring(6, 8)}`;
      },
    },
    {
      title: '运行时间',
      dataIndex: 'duration',
      key: 'duration',
      width: 120,
      align: 'center' as const,
      sorter: (a: TradingDayPerformance, b: TradingDayPerformance) => a.duration - b.duration,
      render: (duration: number) => {
        let color = '#52c41a'; // 绿色：快速
        if (duration > statistics.avgDuration * 1.5) {
          color = '#ff4d4f'; // 红色：慢
        } else if (duration > statistics.avgDuration) {
          color = '#faad14'; // 橙色：中等偏慢
        }
        
        return (
          <Text strong style={{ color }}>
            {duration.toFixed(3)}秒
          </Text>
        );
      },
    },
    {
      title: '相对平均',
      key: 'relative',
      width: 100,
      align: 'center' as const,
      sorter: (a: TradingDayPerformance, b: TradingDayPerformance) => 
        (a.duration / statistics.avgDuration) - (b.duration / statistics.avgDuration),
      render: (_: any, record: TradingDayPerformance) => {
        const ratio = (record.duration / statistics.avgDuration - 1) * 100;
        if (ratio > 50) {
          return <Tag color="error">+{ratio.toFixed(0)}%</Tag>;
        } else if (ratio > 0) {
          return <Tag color="warning">+{ratio.toFixed(0)}%</Tag>;
        } else if (ratio > -20) {
          return <Tag color="success">{ratio.toFixed(0)}%</Tag>;
        } else {
          return <Tag color="success">{ratio.toFixed(0)}%</Tag>;
        }
      },
    },
    {
      title: '日志条数',
      dataIndex: 'logCount',
      key: 'logCount',
      width: 100,
      align: 'center' as const,
      sorter: (a: TradingDayPerformance, b: TradingDayPerformance) => a.logCount - b.logCount,
    },
    {
      title: '开始时间',
      dataIndex: 'startTime',
      key: 'startTime',
      width: 180,
      align: 'center' as const,
      render: (time: string) => {
        const date = new Date(time);
        return date.toLocaleString('zh-CN', { hour12: false });
      },
    },
    {
      title: '结束时间',
      dataIndex: 'endTime',
      key: 'endTime',
      width: 180,
      align: 'center' as const,
      render: (time: string) => {
        const date = new Date(time);
        return date.toLocaleString('zh-CN', { hour12: false });
      },
    },
  ];

  if (!backtestId) {
    return (
      <div style={{ padding: '24px' }}>
        <Alert
          message="提示"
          description="请先运行回测以查看性能分析"
          type="info"
          showIcon
        />
      </div>
    );
  }

  return (
    <div style={{ padding: '24px' }}>
      <Card>
        <Title level={4}>
          <ThunderboltOutlined /> 策略性能分析
        </Title>
        <div style={{ marginBottom: 24 }}>
          <Text type="secondary">
            分析每个交易日的策略运行时间，评估策略的执行效率。运行时间从该交易日的第一条日志到最后一条日志的时间差计算。
          </Text>
        </div>

        {loading ? (
          <div style={{ textAlign: 'center', padding: '100px 0' }}>
            <Spin size="large" tip="正在分析性能数据..." />
          </div>
        ) : performanceData.length > 0 ? (
          <>
            {/* 统计指标卡片 */}
            <Row gutter={16} style={{ marginBottom: 24 }}>
              <Col span={6}>
                <Card>
                  <Statistic
                    title="平均运行时间"
                    value={statistics.avgDuration.toFixed(3)}
                    suffix="秒"
                    prefix={<ClockCircleOutlined />}
                    valueStyle={{ color: '#1890ff' }}
                  />
                </Card>
              </Col>
              <Col span={6}>
                <Card>
                  <Statistic
                    title="最快运行时间"
                    value={statistics.minDuration.toFixed(3)}
                    suffix="秒"
                    prefix={<RocketOutlined />}
                    valueStyle={{ color: '#52c41a' }}
                  />
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    日期: {statistics.fastestDay.replace(/(\d{4})(\d{2})(\d{2})/, '$1-$2-$3')}
                  </Text>
                </Card>
              </Col>
              <Col span={6}>
                <Card>
                  <Statistic
                    title="最慢运行时间"
                    value={statistics.maxDuration.toFixed(3)}
                    suffix="秒"
                    prefix={<ClockCircleOutlined />}
                    valueStyle={{ color: '#ff4d4f' }}
                  />
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    日期: {statistics.slowestDay.replace(/(\d{4})(\d{2})(\d{2})/, '$1-$2-$3')}
                  </Text>
                </Card>
              </Col>
              <Col span={6}>
                <Card>
                  <Statistic
                    title="总交易天数"
                    value={statistics.totalDays}
                    suffix="天"
                    valueStyle={{ color: '#722ed1' }}
                  />
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    总计: {statistics.totalTime.toFixed(1)}秒
                  </Text>
                </Card>
              </Col>
            </Row>

            {/* 性能趋势图 */}
            <Card 
              style={{ marginBottom: 24 }}
              title={
                <span>
                  运行时间趋势图
                  <Tooltip title="展示每个交易日策略的运行时间变化趋势，帮助识别性能瓶颈">
                    <InfoCircleOutlined style={{ marginLeft: 8, color: '#1890ff', cursor: 'pointer' }} />
                  </Tooltip>
                </span>
              }
            >
              <div style={{ width: '100%', minHeight: '400px' }}>
                <ReactECharts
                  option={getPerformanceChartOption()}
                  style={{ width: '100%', height: '400px' }}
                  notMerge={true}
                  lazyUpdate={true}
                />
              </div>
            </Card>

            {/* 详细数据表格 */}
            <Card 
              title={
                <span>
                  每日性能详情
                  <Tooltip title="点击列标题可排序。绿色表示快于平均，橙色表示慢于平均，红色表示明显慢于平均。">
                    <InfoCircleOutlined style={{ marginLeft: 8, color: '#1890ff', cursor: 'pointer' }} />
                  </Tooltip>
                </span>
              }
            >
              <Table
                columns={columns}
                dataSource={performanceData}
                pagination={{
                  pageSize: 20,
                  showTotal: (total) => `共 ${total} 个交易日`,
                  showSizeChanger: true,
                  showQuickJumper: true,
                }}
                size="small"
                scroll={{ x: 1000 }}
                rowKey="date"
              />
            </Card>

            {/* 性能建议 */}
            <Alert
              message="性能优化建议"
              description={
                <div>
                  <div>• 如果运行时间过长，考虑优化策略逻辑，减少不必要的计算</div>
                  <div>• 关注运行时间波动较大的交易日，可能存在特殊情况</div>
                  <div>• 运行时间差异可能与当日交易量、持仓数量、数据处理量相关</div>
                  <div>• 建议平均运行时间控制在合理范围内，确保实盘可用性</div>
                </div>
              }
              type="info"
              showIcon
              style={{ marginTop: 16 }}
            />
          </>
        ) : (
          <Empty 
            description="暂无性能数据，可能是回测还未开始或日志数据不足"
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          />
        )}
      </Card>
    </div>
  );
};

export default PerformanceAnalysis;

