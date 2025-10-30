import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Button,
  Space,
  Tag,
  Select,
  Pagination,
  Modal,
  message,
  Tooltip,
} from 'antd';
import { ReloadOutlined, DeleteOutlined, EyeOutlined } from '@ant-design/icons';
import type { BacktestRecord } from '@/types';
import { backtestApi } from '@/services/api';

interface BacktestManagementProps {
  onViewBacktest: (backId: string) => void;
}

const BacktestManagement: React.FC<BacktestManagementProps> = ({ onViewBacktest }) => {
  const [backtestList, setBacktestList] = useState<BacktestRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedRows, setSelectedRows] = useState<BacktestRecord[]>([]);
  const [filterStatus, setFilterStatus] = useState<string>('');
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [total, setTotal] = useState(0);

  useEffect(() => {
    loadBacktestList();
  }, [currentPage, pageSize, filterStatus]);

  const loadBacktestList = async () => {
    setLoading(true);
    try {
      const result = await backtestApi.getBacktestList(
        currentPage,
        pageSize,
        filterStatus || undefined
      );
      setBacktestList(result.items || []);
      setTotal(result.total || 0);
    } catch (error: any) {
      message.error('加载回测列表失败: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (record: BacktestRecord) => {
    Modal.confirm({
      title: '确认删除',
      content: `确定要删除回测 "${record.strategy_name || record.run_id || record._id}" 吗？此操作将删除所有相关数据且不可恢复！`,
      okText: '确定',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          // 使用 run_id 作为删除的主键（而不是自增的 _id）
          const backId = record.run_id || record._id || '';
          const result = await backtestApi.deleteBacktest(backId);
          const deletedCount = result.data?.deleted_count?.total || 0;
          message.success(`删除成功！共删除 ${deletedCount} 条数据`);
          loadBacktestList();
        } catch (error: any) {
          message.error('删除失败: ' + error.message);
        }
      },
    });
  };

  const handleBatchDelete = async () => {
    if (selectedRows.length === 0) {
      message.warning('请先选择要删除的回测记录');
      return;
    }

    Modal.confirm({
      title: '批量删除确认',
      content: `确定要删除选中的 ${selectedRows.length} 个回测吗？此操作将删除所有相关数据且不可恢复！`,
      okText: '确定',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        let successCount = 0;
        let failCount = 0;

        for (const record of selectedRows) {
          try {
            // 使用 run_id 作为删除的主键（而不是自增的 _id）
            const backId = record.run_id || record._id || '';
            await backtestApi.deleteBacktest(backId);
            successCount++;
          } catch (error) {
            failCount++;
          }
        }

        message.success(`批量删除完成：成功 ${successCount}，失败 ${failCount}`);
        setSelectedRows([]);
        loadBacktestList();
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
      title: '回测ID',
      key: 'id',
      width: 220,
      ellipsis: true,
      render: (record: BacktestRecord) => (
        <Tooltip title={record.run_id || record._id}>
          {record.run_id || record._id}
        </Tooltip>
      ),
    },
    {
      title: '策略名称',
      dataIndex: 'strategy_name',
      key: 'strategy_name',
      width: 150,
      render: (text: string) => text || 'N/A',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => {
        const colorMap: Record<string, string> = {
          running: 'processing',
          completed: 'success',
          failed: 'error',
        };
        const textMap: Record<string, string> = {
          running: '运行中',
          completed: '已完成',
          failed: '失败',
        };
        return <Tag color={colorMap[status] || 'default'}>{textMap[status] || status}</Tag>;
      },
    },
    {
      title: '收益率',
      dataIndex: 'back_profit',
      key: 'back_profit',
      width: 120,
      align: 'right' as const,
      render: (profit?: number) => {
        if (profit === undefined || profit === null) return '-';
        const color = profit >= 0 ? '#52c41a' : '#ff4d4f';
        return <span style={{ color, fontWeight: 'bold' }}>{(profit * 100).toFixed(2)}%</span>;
      },
    },
    {
      title: '年化收益',
      dataIndex: 'back_profit_year',
      key: 'back_profit_year',
      width: 120,
      align: 'right' as const,
      render: (profit?: number) => {
        if (profit === undefined || profit === null) return '-';
        return `${(profit * 100).toFixed(2)}%`;
      },
    },
    {
      title: '夏普比率',
      dataIndex: 'sharpe',
      key: 'sharpe',
      width: 100,
      align: 'right' as const,
      render: (sharpe?: number) => {
        if (sharpe === undefined || sharpe === null) return '-';
        return sharpe.toFixed(2);
      },
    },
    {
      title: '最大回撤',
      dataIndex: 'max_drawdown',
      key: 'max_drawdown',
      width: 120,
      align: 'right' as const,
      render: (drawdown?: number) => {
        if (drawdown === undefined || drawdown === null) return '-';
        return <span style={{ color: '#ff4d4f' }}>{(drawdown * 100).toFixed(2)}%</span>;
      },
    },
    {
      title: '回测区间',
      key: 'date_range',
      width: 200,
      render: (record: BacktestRecord) =>
        `${record.start_date || 'N/A'} ~ ${record.end_date || 'N/A'}`,
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: formatDateTime,
    },
    {
      title: '操作',
      key: 'action',
      width: 180,
      fixed: 'right' as const,
      render: (record: BacktestRecord) => (
        <Space size="small">
          <Button
            size="small"
            icon={<EyeOutlined />}
            onClick={() => onViewBacktest(record.run_id || record._id || '')}
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

  const rowSelection = {
    selectedRowKeys: selectedRows.map((r) => r.run_id || r._id || ''),
    onChange: (_: React.Key[], selectedRecords: BacktestRecord[]) => {
      setSelectedRows(selectedRecords);
    },
  };

  return (
    <div style={{ padding: 20 }}>
      <Card
        title={
          <div>
            <h2 style={{ margin: 0 }}>回测记录管理</h2>
            <p style={{ margin: '5px 0 0 0', color: '#909399', fontSize: 14, fontWeight: 'normal' }}>
              查看、管理和删除历史回测记录
            </p>
          </div>
        }
        extra={
          <Space>
            <Select
              placeholder="筛选状态"
              value={filterStatus || undefined}
              onChange={setFilterStatus}
              allowClear
              style={{ width: 150 }}
            >
              <Select.Option value="">全部</Select.Option>
              <Select.Option value="running">运行中</Select.Option>
              <Select.Option value="completed">已完成</Select.Option>
              <Select.Option value="failed">失败</Select.Option>
            </Select>
            <Button icon={<ReloadOutlined />} onClick={loadBacktestList} loading={loading}>
              刷新
            </Button>
            <Button
              danger
              icon={<DeleteOutlined />}
              onClick={handleBatchDelete}
              disabled={selectedRows.length === 0}
            >
              批量删除 ({selectedRows.length})
            </Button>
          </Space>
        }
      >
        <Table
          columns={columns}
          dataSource={backtestList}
          loading={loading}
          rowSelection={rowSelection}
          pagination={false}
          scroll={{ x: 1500 }}
          rowKey={(record) => record.run_id || record._id || ''}
        />
        <div style={{ marginTop: 20, textAlign: 'center' }}>
          <Pagination
            current={currentPage}
            pageSize={pageSize}
            total={total}
            showSizeChanger
            showQuickJumper
            showTotal={(total) => `共 ${total} 条`}
            pageSizeOptions={[10, 20, 50, 100]}
            onChange={(page, size) => {
              setCurrentPage(page);
              setPageSize(size);
            }}
          />
        </div>
      </Card>
    </div>
  );
};

export default BacktestManagement;

