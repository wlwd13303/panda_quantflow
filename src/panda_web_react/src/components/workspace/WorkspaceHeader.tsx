import React from 'react';
import { Layout, Space, Button, Select, Badge, Tooltip } from 'antd';
import {
  PlusOutlined,
  FolderOutlined,
  BarChartOutlined,
  CodeOutlined,
} from '@ant-design/icons';
import type { Strategy, BacktestRecord } from '@/types';

const { Header } = Layout;

interface WorkspaceHeaderProps {
  strategies: Strategy[];
  runningBacktests: BacktestRecord[];
  onNewStrategy: () => void;
  onOpenStrategy: (strategyId: string) => void;
  onOpenBacktest: (backtestId: string) => void;
  onOpenManagement: () => void;
}

const WorkspaceHeader: React.FC<WorkspaceHeaderProps> = ({
  strategies,
  runningBacktests,
  onNewStrategy,
  onOpenStrategy,
  onOpenBacktest,
  onOpenManagement,
}) => {
  // 格式化回测显示文本
  const formatBacktestLabel = (backtest: BacktestRecord) => {
    const statusIcon = backtest.status === 'running' ? '⚡' : '✅';
    
    // 优先使用策略名称，如果没有或是纯数字则使用更有意义的描述
    let displayName = backtest.strategy_name;
    if (!displayName || /^\d+$/.test(displayName.trim())) {
      // 如果策略名称为空或只是纯数字，则使用日期或ID
      if (backtest.created_at) {
        const date = new Date(backtest.created_at);
        displayName = `回测-${date.toLocaleDateString('zh-CN')}`;
      } else {
        displayName = `回测-${backtest._id?.substring(0, 8) || backtest.run_id?.substring(0, 8) || '未命名'}`;
      }
    }
    
    // 添加状态信息
    let statusInfo = '';
    if (backtest.status === 'running') {
      const progress = Math.round((backtest as any).progress || 0);
      statusInfo = ` (进度: ${progress}%)`;
    } else if (backtest.status === 'completed' && backtest.back_profit !== undefined) {
      const profit = (backtest.back_profit * 100).toFixed(2);
      statusInfo = ` (收益: ${profit}%)`;
    }
    
    return `${statusIcon} ${displayName}${statusInfo}`;
  };

  return (
    <Header
      style={{
        background: '#fff',
        padding: '0 24px',
        borderBottom: '1px solid #e8e8e8',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center' }}>
        <h2 style={{ margin: 0, marginRight: 24 }}>
          🐼 PandaAI QuantFlow
        </h2>
        
        <Space size="middle">
          {/* 策略库下拉 */}
          <Tooltip title="打开策略">
            <Select
              placeholder={
                <span>
                  <CodeOutlined /> 策略库
                </span>
              }
              style={{ minWidth: 200 }}
              onChange={onOpenStrategy}
              value={undefined}
              showSearch
              optionFilterProp="children"
              dropdownMatchSelectWidth={300}
            >
              {strategies.map((strategy) => (
                <Select.Option key={strategy.id || strategy._id} value={strategy.id || strategy._id || ''}>
                  <Space>
                    <CodeOutlined />
                    <span>{strategy.name}</span>
                    {strategy.backtest_count !== undefined && strategy.backtest_count > 0 && (
                      <Badge
                        count={strategy.backtest_count}
                        style={{ backgroundColor: '#52c41a' }}
                      />
                    )}
                  </Space>
                </Select.Option>
              ))}
            </Select>
          </Tooltip>

          {/* 运行中的回测下拉 */}
          {runningBacktests.length > 0 && (
            <Tooltip title="查看回测">
              <Select
                placeholder={
                  <Space>
                    <BarChartOutlined />
                    <Badge count={runningBacktests.length} offset={[10, 0]}>
                      <span>运行中的回测</span>
                    </Badge>
                  </Space>
                }
                style={{ minWidth: 220 }}
                onChange={onOpenBacktest}
                value={undefined}
                dropdownMatchSelectWidth={350}
              >
              {runningBacktests.map((backtest) => (
                <Select.Option key={backtest._id || backtest.run_id} value={backtest._id || backtest.run_id || ''}>
                  <Space>
                    <span>{formatBacktestLabel(backtest)}</span>
                    {backtest.start_date && backtest.end_date && (
                      <span style={{ fontSize: '12px', color: '#999' }}>
                        [{backtest.start_date} ~ {backtest.end_date}]
                      </span>
                    )}
                  </Space>
                </Select.Option>
              ))}
              </Select>
            </Tooltip>
          )}
        </Space>
      </div>

      <Space>
        <Button
          icon={<PlusOutlined />}
          onClick={onNewStrategy}
          type="default"
        >
          新建策略
        </Button>
        
        <Button
          icon={<FolderOutlined />}
          onClick={onOpenManagement}
        >
          管理中心
        </Button>
      </Space>
    </Header>
  );
};

export default WorkspaceHeader;

