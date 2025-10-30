import React from 'react';
import { Tabs, Modal } from 'antd';
import {
  CodeOutlined,
  BarChartOutlined,
  FolderOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons';
import type { WorkspaceTab } from '@/types';

const { confirm } = Modal;

interface WorkspaceTabsProps {
  tabs: WorkspaceTab[];
  activeTabId: string;
  onTabChange: (tabId: string) => void;
  onTabClose: (tabId: string) => void;
}

const WorkspaceTabs: React.FC<WorkspaceTabsProps> = ({
  tabs,
  activeTabId,
  onTabChange,
  onTabClose,
}) => {
  // 获取Tab图标
  const getTabIcon = (tab: WorkspaceTab) => {
    switch (tab.type) {
      case 'strategy':
        return <CodeOutlined />;
      case 'backtest':
        return <BarChartOutlined />;
      case 'management':
        return <FolderOutlined />;
      default:
        return null;
    }
  };

  // 获取Tab标题（包含状态标识）
  const getTabLabel = (tab: WorkspaceTab) => {
    let label = tab.title;
    
    // 策略Tab：显示未保存标记
    if (tab.type === 'strategy' && tab.strategyData?.unsavedChanges) {
      label = `${label} *`;
    }
    
    // 回测Tab：显示状态标记
    if (tab.type === 'backtest' && tab.backtestData) {
      const { status, progress } = tab.backtestData;
      if (status === 'running') {
        label = `${label} ⚡ ${progress ? `${Math.round(progress)}%` : '运行中'}`;
      } else if (status === 'completed') {
        label = `${label} ✅`;
      } else if (status === 'failed') {
        label = `${label} ❌`;
      }
    }
    
    return label;
  };

  // 处理Tab关闭
  const handleTabClose = (tabId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    
    const tab = tabs.find(t => t.id === tabId);
    if (!tab) return;

    // 如果是策略Tab且有未保存的修改，需要确认
    if (tab.type === 'strategy' && tab.strategyData?.unsavedChanges) {
      confirm({
        title: '确认关闭',
        icon: <ExclamationCircleOutlined />,
        content: `策略 "${tab.title}" 有未保存的修改，确定要关闭吗？`,
        okText: '关闭',
        okType: 'danger',
        cancelText: '取消',
        onOk: () => {
          onTabClose(tabId);
        },
      });
    } else {
      onTabClose(tabId);
    }
  };

  // 转换为Ant Design Tabs的items格式
  const tabItems = tabs.map((tab) => ({
    key: tab.id,
    label: (
      <span>
        {getTabIcon(tab)}
        <span style={{ marginLeft: 8 }}>{getTabLabel(tab)}</span>
      </span>
    ),
    closable: tab.closable,
  }));

  return (
    <Tabs
      type="editable-card"
      activeKey={activeTabId}
      onChange={onTabChange}
      onEdit={(targetKey, action) => {
        if (action === 'remove' && typeof targetKey === 'string') {
          const tab = tabs.find(t => t.id === targetKey);
          if (tab?.closable) {
            handleTabClose(targetKey, {} as React.MouseEvent);
          }
        }
      }}
      items={tabItems}
      hideAdd
      style={{
        margin: 0,
        padding: '0 16px',
        background: '#fff',
      }}
      tabBarStyle={{
        margin: 0,
        borderBottom: '1px solid #e8e8e8',
      }}
    />
  );
};

export default WorkspaceTabs;

