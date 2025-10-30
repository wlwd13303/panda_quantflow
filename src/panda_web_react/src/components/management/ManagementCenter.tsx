import React, { useState } from 'react';
import { Layout, Menu, Card } from 'antd';
import {
  CodeOutlined,
  BarChartOutlined,
  EyeOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import StrategyList from './StrategyList';
import BacktestManagement from '../BacktestManagement';
import BacktestMonitor from '../BacktestMonitor';
import type { Strategy } from '@/types';

const { Sider, Content } = Layout;

type MenuKey = 'strategies' | 'backtests' | 'monitor' | 'settings';

interface ManagementCenterProps {
  strategies: Strategy[];
  strategiesLoading?: boolean;
  onEditStrategy: (strategyId: string) => void;
  onDeleteStrategy: (strategyId: string) => Promise<void>;
  onNewStrategy: () => void;
  onRefreshStrategies: () => void;
  onViewBacktest: (backtestId: string) => void;
}

const ManagementCenter: React.FC<ManagementCenterProps> = ({
  strategies,
  strategiesLoading = false,
  onEditStrategy,
  onDeleteStrategy,
  onNewStrategy,
  onRefreshStrategies,
  onViewBacktest,
}) => {
  const [selectedSection, setSelectedSection] = useState<MenuKey>('strategies');

  const menuItems = [
    {
      key: 'strategies',
      icon: <CodeOutlined />,
      label: '策略库',
    },
    {
      key: 'backtests',
      icon: <BarChartOutlined />,
      label: '回测历史',
    },
    {
      key: 'monitor',
      icon: <EyeOutlined />,
      label: '实时监控',
    },
    {
      key: 'settings',
      icon: <SettingOutlined />,
      label: '系统设置',
    },
  ];

  const renderContent = () => {
    switch (selectedSection) {
      case 'strategies':
        return (
          <Card
            title="策略库管理"
            bordered={false}
          >
            <StrategyList
              strategies={strategies}
              loading={strategiesLoading}
              onEdit={onEditStrategy}
              onDelete={onDeleteStrategy}
              onNew={onNewStrategy}
              onRefresh={onRefreshStrategies}
            />
          </Card>
        );

      case 'backtests':
        return <BacktestManagement onViewBacktest={onViewBacktest} />;

      case 'monitor':
        return (
          <Card
            title="实时监控"
            bordered={false}
          >
            <BacktestMonitor />
          </Card>
        );

      case 'settings':
        return (
          <Card
            title="系统设置"
            bordered={false}
          >
            <div style={{ padding: '40px 0', textAlign: 'center', color: '#999' }}>
              <SettingOutlined style={{ fontSize: 48, marginBottom: 16 }} />
              <p>系统设置功能开发中...</p>
            </div>
          </Card>
        );

      default:
        return null;
    }
  };

  return (
    <Layout style={{ height: '100%', background: '#fff' }}>
      <Sider
        width={200}
        style={{
          background: '#fff',
          borderRight: '1px solid #e8e8e8',
        }}
      >
        <Menu
          mode="inline"
          selectedKeys={[selectedSection]}
          onClick={({ key }) => setSelectedSection(key as MenuKey)}
          style={{ height: '100%', borderRight: 0 }}
          items={menuItems}
        />
      </Sider>

      <Content style={{ padding: '24px', overflow: 'auto', background: '#f5f5f5' }}>
        {renderContent()}
      </Content>
    </Layout>
  );
};

export default ManagementCenter;

