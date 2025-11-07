import React, { useState, useEffect, useRef } from 'react';
import { Card, Empty, Spin, Tag, Button, Space, Typography, Select } from 'antd';
import { ReloadOutlined, DownOutlined } from '@ant-design/icons';
import { backtestApi } from '@/services/api';
import type { BacktestLog } from '@/types';

const { Text } = Typography;

interface LogOutputProps {
  backtestId?: string;
  backtesting?: boolean;
  autoRefresh?: boolean;
  refreshInterval?: number;
}

const LogOutput: React.FC<LogOutputProps> = ({
  backtestId,
  backtesting = false,
  autoRefresh = true,
  refreshInterval = 2000,
}) => {
  const [logs, setLogs] = useState<BacktestLog[]>([]);
  const [loading, setLoading] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [lastSort, setLastSort] = useState<number | undefined>(undefined);
  const [logLevel, setLogLevel] = useState<string>('all');
  const logContainerRef = useRef<HTMLDivElement>(null);
  const refreshTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // 获取日志级别颜色
  const getLogLevelColor = (level?: string): string => {
    if (!level) return 'default';
    const levelLower = level.toLowerCase();
    if (levelLower.includes('error') || levelLower === '3') return 'red';
    if (levelLower.includes('warn') || levelLower === '2') return 'orange';
    if (levelLower.includes('info') || levelLower === '1') return 'blue';
    if (levelLower.includes('debug') || levelLower === '0') return 'cyan';
    return 'default';
  };

  // 获取日志级别文本
  const getLogLevelText = (level?: string): string => {
    if (!level) return 'UNKNOWN';
    const levelLower = level.toLowerCase();
    if (levelLower.includes('error') || levelLower === '3') return 'ERROR';
    if (levelLower.includes('warn') || levelLower === '2') return 'WARN';
    if (levelLower.includes('info') || levelLower === '1') return 'INFO';
    if (levelLower.includes('debug') || levelLower === '0') return 'DEBUG';
    return level.toUpperCase();
  };

  // 格式化时间
  const formatTime = (timeStr?: string): string => {
    if (!timeStr) return '';
    try {
      const date = new Date(timeStr);
      return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false,
      });
    } catch {
      return timeStr;
    }
  };

  // 加载日志
  const loadLogs = async (loadMore: boolean = false) => {
    if (!backtestId) return;

    setLoading(true);
    try {
      const currentLastSort = loadMore ? lastSort : undefined;
      const response = await backtestApi.getLogs(backtestId, currentLastSort, 100);
      
      console.log('日志API响应:', response);
      console.log('日志数量:', response.items?.length);
      if (response.items && response.items.length > 0) {
        console.log('第一条日志示例:', response.items[0]);
      }
      
      if (loadMore) {
        // 加载更多时，追加到现有日志
        setLogs((prevLogs) => [...prevLogs, ...response.items]);
      } else {
        // 首次加载或刷新时，替换日志
        setLogs(response.items);
      }

      // 更新游标
      if (response.items.length > 0) {
        const lastItem = response.items[response.items.length - 1];
        console.log('最后一条日志:', lastItem);
        const sortValue = lastItem.sort ? parseInt(String(lastItem.sort)) : undefined;
        setLastSort(sortValue);
        setHasMore(response.items.length >= response.cursor.limit);
      } else {
        setHasMore(false);
      }
    } catch (error) {
      console.error('加载日志失败:', error);
    } finally {
      setLoading(false);
    }
  };

  // 滚动到底部
  const scrollToBottom = () => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  };

  // 首次加载
  useEffect(() => {
    if (backtestId) {
      loadLogs(false);
    }
  }, [backtestId]);

  // 自动刷新
  useEffect(() => {
    if (backtesting && autoRefresh && backtestId) {
      refreshTimerRef.current = setInterval(() => {
        loadLogs(false);
      }, refreshInterval);

      return () => {
        if (refreshTimerRef.current) {
          clearInterval(refreshTimerRef.current);
        }
      };
    }
  }, [backtesting, autoRefresh, refreshInterval, backtestId]);

  // 日志更新后自动滚动
  useEffect(() => {
    scrollToBottom();
  }, [logs]);

  // 过滤日志
  const filteredLogs = logs.filter((log) => {
    // 先检查日志内容是否存在
    const logContent = log.run_info || log.opz_params_str || '';
    if (!logContent) {
      return false; // 过滤掉没有内容的日志
    }
    
    // 再检查日志级别过滤
    if (logLevel === 'all') return true;
    const levelLower = log.level?.toLowerCase() || '';
    return (
      (logLevel === 'error' && (levelLower.includes('error') || levelLower === '3')) ||
      (logLevel === 'warn' && (levelLower.includes('warn') || levelLower === '2')) ||
      (logLevel === 'info' && (levelLower.includes('info') || levelLower === '1')) ||
      (logLevel === 'debug' && (levelLower.includes('debug') || levelLower === '0'))
    );
  });

  return (
    <Card
      style={{ margin: 20 }}
      title="日志输出"
      extra={
        <Space>
          <Select
            value={logLevel}
            onChange={setLogLevel}
            style={{ width: 120 }}
            size="small"
          >
            <Select.Option value="all">全部</Select.Option>
            <Select.Option value="error">错误</Select.Option>
            <Select.Option value="warn">警告</Select.Option>
            <Select.Option value="info">信息</Select.Option>
            <Select.Option value="debug">调试</Select.Option>
          </Select>
          <Button
            icon={<ReloadOutlined />}
            onClick={() => loadLogs(false)}
            loading={loading}
            size="small"
          >
            刷新
          </Button>
          {hasMore && (
            <Button
              icon={<DownOutlined />}
              onClick={() => loadLogs(true)}
              loading={loading}
              size="small"
            >
              加载更多
            </Button>
          )}
        </Space>
      }
    >
      {!backtestId ? (
        <Empty description="暂无回测ID" />
      ) : (
        <div
          ref={logContainerRef}
          style={{
            background: '#1e1e1e',
            padding: 16,
            borderRadius: 4,
            fontFamily: 'Consolas, Monaco, "Courier New", monospace',
            fontSize: 13,
            maxHeight: 'calc(100vh - 280px)',
            overflow: 'auto',
            color: '#d4d4d4',
            lineHeight: 1.6,
          }}
        >
          {filteredLogs.length === 0 ? (
            <div style={{ textAlign: 'center', padding: 40, color: '#888' }}>
              {loading ? (
                <Spin />
              ) : (
                <div>
                  <div>暂无日志数据</div>
                  {logs.length > 0 && (
                    <div style={{ fontSize: 12, marginTop: 8, color: '#666' }}>
                      (共有 {logs.length} 条日志，但被过滤条件过滤掉了)
                    </div>
                  )}
                  {backtestId && (
                    <div style={{ fontSize: 12, marginTop: 8, color: '#666' }}>
                      回测ID: {backtestId}
                    </div>
                  )}
                </div>
              )}
            </div>
          ) : (
            filteredLogs.map((log, index) => {
              const displayTime = log.exhibit_time || log.insert_time || '';
              // 优先使用 run_info，如果没有则使用 opz_params_str
              const logContent = log.run_info || log.opz_params_str || '';
              const level = log.level || '';

              return (
                <div
                  key={`${log.id || log._id || index}_${log.sort || index}`}
                  style={{
                    marginBottom: 8,
                    padding: '4px 0',
                    borderBottom: index < filteredLogs.length - 1 ? '1px solid #333' : 'none',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}>
                    {displayTime && (
                      <Text
                        style={{
                          color: '#858585',
                          fontSize: 12,
                          minWidth: 180,
                          flexShrink: 0,
                        }}
                      >
                        {formatTime(displayTime)}
                      </Text>
                    )}
                    <Tag
                      color={getLogLevelColor(level)}
                      style={{
                        margin: 0,
                        fontSize: 11,
                        height: 20,
                        lineHeight: '18px',
                        flexShrink: 0,
                      }}
                    >
                      {getLogLevelText(level)}
                    </Tag>
                    {log.source && (
                      <Text
                        style={{
                          color: '#569cd6',
                          fontSize: 12,
                          flexShrink: 0,
                        }}
                      >
                        [{log.source}]
                      </Text>
                    )}
                    <Text
                      style={{
                        color: '#d4d4d4',
                        fontSize: 13,
                        flex: 1,
                        wordBreak: 'break-word',
                        whiteSpace: 'pre-wrap',
                      }}
                    >
                      {logContent || '(空日志)'}
                    </Text>
                  </div>
                </div>
              );
            })
          )}
          {loading && filteredLogs.length > 0 && (
            <div style={{ textAlign: 'center', padding: 16 }}>
              <Spin size="small" />
            </div>
          )}
        </div>
      )}
    </Card>
  );
};

export default LogOutput;

