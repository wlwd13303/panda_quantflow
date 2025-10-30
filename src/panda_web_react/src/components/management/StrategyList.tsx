import React, { useState } from 'react';
import {
  Table,
  Button,
  Space,
  Tag,
  Modal,
  message,
  Tooltip,
  Input,
} from 'antd';
import {
  EditOutlined,
  DeleteOutlined,
  EyeOutlined,
  SearchOutlined,
  PlusOutlined,
} from '@ant-design/icons';
import type { Strategy } from '@/types';

interface StrategyListProps {
  strategies: Strategy[];
  loading?: boolean;
  onEdit: (strategyId: string) => void;
  onDelete: (strategyId: string) => Promise<void>;
  onNew: () => void;
  onRefresh: () => void;
}

const StrategyList: React.FC<StrategyListProps> = ({
  strategies,
  loading = false,
  onEdit,
  onDelete,
  onNew,
  onRefresh,
}) => {
  const [searchText, setSearchText] = useState('');

  const handleDelete = (strategy: Strategy) => {
    Modal.confirm({
      title: '确认删除',
      content: `确定要删除策略 "${strategy.name}" 吗？此操作不可恢复！`,
      okText: '确定',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          await onDelete(strategy.id || strategy._id || '');
          message.success('删除成功');
          onRefresh();
        } catch (error: any) {
          message.error('删除失败: ' + error.message);
        }
      },
    });
  };

  const formatDateTime = (dateTime?: string) => {
    if (!dateTime) return 'N/A';
    try {
      const date = new Date(dateTime);
      return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch (error) {
      return String(dateTime);
    }
  };

  const columns = [
    {
      title: '策略名称',
      dataIndex: 'name',
      key: 'name',
      width: 200,
      filteredValue: searchText ? [searchText] : null,
      onFilter: (value: any, record: Strategy) =>
        record.name.toLowerCase().includes(value.toLowerCase()) ||
        (record.description?.toLowerCase() || '').includes(value.toLowerCase()),
      render: (text: string) => <strong>{text}</strong>,
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
      render: (text: string) => (
        <Tooltip title={text}>
          <span>{text || '-'}</span>
        </Tooltip>
      ),
    },
    {
      title: '回测次数',
      dataIndex: 'backtest_count',
      key: 'backtest_count',
      width: 100,
      align: 'center' as const,
      render: (count: number) => (
        <Tag color={count > 0 ? 'blue' : 'default'}>
          {count || 0}
        </Tag>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: formatDateTime,
      sorter: (a: Strategy, b: Strategy) => {
        const dateA = new Date(a.created_at || 0).getTime();
        const dateB = new Date(b.created_at || 0).getTime();
        return dateA - dateB;
      },
    },
    {
      title: '最后修改',
      dataIndex: 'updated_at',
      key: 'updated_at',
      width: 180,
      render: formatDateTime,
      sorter: (a: Strategy, b: Strategy) => {
        const dateA = new Date(a.updated_at || 0).getTime();
        const dateB = new Date(b.updated_at || 0).getTime();
        return dateA - dateB;
      },
      defaultSortOrder: 'descend' as const,
    },
    {
      title: '操作',
      key: 'action',
      width: 200,
      fixed: 'right' as const,
      render: (record: Strategy) => (
        <Space size="small">
          <Button
            size="small"
            type="primary"
            icon={<EditOutlined />}
            onClick={() => onEdit(record.id || record._id || '')}
          >
            编辑
          </Button>
          <Button
            size="small"
            icon={<EyeOutlined />}
            onClick={() => onEdit(record.id || record._id || '')}
          >
            查看
          </Button>
          <Button
            size="small"
            danger
            icon={<DeleteOutlined />}
            onClick={() => handleDelete(record)}
          >
            删除
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
        <Space>
          <Input
            placeholder="搜索策略名称或描述"
            prefix={<SearchOutlined />}
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            style={{ width: 300 }}
            allowClear
          />
        </Space>
        <Space>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={onNew}
          >
            新建策略
          </Button>
        </Space>
      </div>

      <Table
        columns={columns}
        dataSource={strategies}
        loading={loading}
        rowKey={(record) => record.id || record._id || ''}
        pagination={{
          pageSize: 20,
          showTotal: (total) => `共 ${total} 个策略`,
          showSizeChanger: true,
          showQuickJumper: true,
        }}
        scroll={{ x: 1200 }}
      />
    </div>
  );
};

export default StrategyList;

