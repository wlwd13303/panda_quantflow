import React, { useState } from 'react';
import {
  Card,
  Form,
  Input,
  InputNumber,
  Button,
  Space,
  Alert,
  Checkbox,
  Collapse,
  List,
  Tag,
  Divider,
  DatePicker,
  Select,
} from 'antd';
import {
  SaveOutlined,
  PlayCircleOutlined,
  EyeOutlined,
} from '@ant-design/icons';
import type { BacktestConfig, BacktestRecord } from '@/types';
import dayjs from 'dayjs';

const { TextArea } = Input;

interface StrategyToolbarProps {
  strategyId: string;
  strategyName: string;
  description?: string;
  unsavedChanges: boolean;
  defaultConfig?: BacktestConfig;
  relatedBacktests?: BacktestRecord[];
  onSaveStrategy: (data: { name: string; description?: string }) => void;
  onUpdateStrategyInfo: (data: { name?: string; description?: string }) => void;
  onStartBacktest: (config: BacktestConfig, backtestName: string, saveAsDefault: boolean) => void;
  onViewBacktest: (backtestId: string) => void;
  saving?: boolean;
  running?: boolean;
}

const StrategyToolbar: React.FC<StrategyToolbarProps> = ({
  strategyId,
  strategyName,
  description = '',
  unsavedChanges,
  defaultConfig,
  relatedBacktests = [],
  onSaveStrategy,
  onUpdateStrategyInfo,
  onStartBacktest,
  onViewBacktest,
  saving = false,
  running = false,
}) => {
  const [form] = Form.useForm();
  const [backtestForm] = Form.useForm();
  const [saveAsDefault, setSaveAsDefault] = useState(false);

  // 初始化回测配置表单
  React.useEffect(() => {
    const config = defaultConfig || {
      start_capital: 1000,
      start_date: '20240101',
      end_date: '20240201',
      frequency: '1d',
      commission_rate: 1,
      standard_symbol: '000001.SH',
      matching_type: 1,
    };
    backtestForm.setFieldsValue({
      backtest_name: '',
      ...config,
    });
  }, [defaultConfig, backtestForm]);

  // 处理保存策略
  const handleSave = () => {
    form.validateFields().then((values) => {
      onSaveStrategy({
        name: values.strategy_name,
        description: values.description,
      });
    });
  };

  // 处理开始回测
  const handleStartBacktest = () => {
    backtestForm.validateFields().then((values) => {
      const config: BacktestConfig = {
        start_capital: values.start_capital,
        start_date: values.start_date,
        end_date: values.end_date,
        frequency: values.frequency,
        commission_rate: values.commission_rate,
        standard_symbol: values.standard_symbol,
        matching_type: values.matching_type,
      };
      onStartBacktest(config, values.backtest_name || '', saveAsDefault);
    });
  };

  // 格式化回测列表项
  const formatBacktestItem = (item: BacktestRecord) => {
    const statusColor = {
      running: 'processing',
      completed: 'success',
      failed: 'error',
      pending: 'default',
    };
    const statusText = {
      running: '运行中',
      completed: '已完成',
      failed: '失败',
      pending: '待运行',
    };
    return {
      ...item,
      statusColor: statusColor[item.status] || 'default',
      statusText: statusText[item.status] || item.status,
    };
  };

  return (
    <div style={{ padding: '16px', overflowY: 'auto', height: '100%' }}>
      {/* 策略信息 */}
      <Card
        title="💾 策略信息"
        size="small"
        style={{ marginBottom: 16 }}
      >
        <Form
          form={form}
          layout="vertical"
          initialValues={{
            strategy_name: strategyName,
            description: description,
          }}
          onValuesChange={(changedValues) => {
            onUpdateStrategyInfo(changedValues);
          }}
        >
          <Form.Item
            label="策略名称"
            name="strategy_name"
            rules={[{ required: true, message: '请输入策略名称' }]}
          >
            <Input placeholder="请输入策略名称" />
          </Form.Item>

          <Form.Item label="策略描述" name="description">
            <TextArea
              rows={3}
              placeholder="请输入策略描述（可选）"
              showCount
              maxLength={500}
            />
          </Form.Item>

          <Button
            type="primary"
            icon={<SaveOutlined />}
            onClick={handleSave}
            loading={saving}
            block
            disabled={!unsavedChanges && strategyId !== 'new'}
          >
            {strategyId === 'new' ? '保存新策略' : '保存修改'}
          </Button>

          {unsavedChanges && (
            <Alert
              message="有未保存的修改"
              type="warning"
              showIcon
              style={{ marginTop: 12 }}
            />
          )}
        </Form>
      </Card>

      {/* 快速回测 */}
      <Card
        title="🚀 快速回测"
        size="small"
        style={{ marginBottom: 16 }}
      >
        <Form
          form={backtestForm}
          layout="vertical"
          size="small"
        >
          <Form.Item
            label="回测名称"
            name="backtest_name"
            tooltip="留空则自动生成"
          >
            <Input placeholder="留空则自动生成" />
          </Form.Item>

          <Form.Item
            label="初始资金(万)"
            name="start_capital"
            rules={[{ required: true, message: '请输入初始资金' }]}
          >
            <InputNumber
              style={{ width: '100%' }}
              min={1}
              max={100000}
              placeholder="1000"
            />
          </Form.Item>

          <Form.Item
            label="开始日期"
            name="start_date"
            rules={[{ required: true, message: '请选择开始日期' }]}
          >
            <Input placeholder="YYYYMMDD" />
          </Form.Item>

          <Form.Item
            label="结束日期"
            name="end_date"
            rules={[{ required: true, message: '请选择结束日期' }]}
          >
            <Input placeholder="YYYYMMDD" />
          </Form.Item>

          <Collapse 
            ghost 
            size="small"
            items={[
              {
                key: '1',
                label: '更多配置',
                children: (
                  <>
                    <Form.Item
                      label="佣金费率(‰)"
                      name="commission_rate"
                    >
                      <InputNumber
                        style={{ width: '100%' }}
                        min={0}
                        max={10}
                        step={0.1}
                        precision={2}
                      />
                    </Form.Item>

                    <Form.Item
                      label="数据频率"
                      name="frequency"
                    >
                      <Select>
                        <Select.Option value="1d">日线</Select.Option>
                        <Select.Option value="1m">分钟线</Select.Option>
                      </Select>
                    </Form.Item>

                    <Form.Item
                      label="基准指数"
                      name="standard_symbol"
                    >
                      <Select>
                        <Select.Option value="000001.SH">上证指数</Select.Option>
                        <Select.Option value="000300.SH">沪深300</Select.Option>
                        <Select.Option value="000905.SH">中证500</Select.Option>
                      </Select>
                    </Form.Item>
                  </>
                ),
              },
            ]}
          />

          <Space direction="vertical" style={{ width: '100%', marginTop: 16 }}>
            <Button
              type="primary"
              icon={<PlayCircleOutlined />}
              onClick={handleStartBacktest}
              loading={running}
              block
              disabled={strategyId === 'new' || unsavedChanges}
            >
              开始回测
            </Button>

            {(strategyId === 'new' || unsavedChanges) && (
              <Alert
                message="请先保存策略后再运行回测"
                type="info"
                showIcon
                style={{ fontSize: 12 }}
              />
            )}

            <Checkbox
              checked={saveAsDefault}
              onChange={(e) => setSaveAsDefault(e.target.checked)}
            >
              保存为默认配置
            </Checkbox>
          </Space>
        </Form>
      </Card>

      {/* 基于此策略的回测历史 */}
      {strategyId !== 'new' && (
        <Card
          title="📊 回测历史"
          size="small"
          extra={<span style={{ fontSize: 12, fontWeight: 'normal' }}>共 {relatedBacktests.length} 个</span>}
        >
          {relatedBacktests.length > 0 ? (
            <List
              size="small"
              dataSource={relatedBacktests.slice(0, 10)}
              renderItem={(item) => {
                const formatted = formatBacktestItem(item);
                return (
                  <List.Item
                    actions={[
                      <Button
                        size="small"
                        type="link"
                        icon={<EyeOutlined />}
                        onClick={() => onViewBacktest(item.run_id || item._id || '')}
                      >
                        查看
                      </Button>,
                    ]}
                  >
                    <List.Item.Meta
                      title={
                        <Space size="small">
                          <span style={{ fontSize: 13 }}>
                            {(() => {
                              let displayName = item.strategy_name;
                              if (!displayName || /^\d+$/.test(displayName.trim())) {
                                if (item.created_at) {
                                  const date = new Date(item.created_at);
                                  displayName = `回测-${date.toLocaleDateString('zh-CN')}`;
                                } else {
                                  displayName = `回测-${item._id?.substring(0, 8) || '未命名'}`;
                                }
                              }
                              return displayName;
                            })()}
                          </span>
                          <Tag color={formatted.statusColor} style={{ fontSize: 11 }}>
                            {formatted.statusText}
                          </Tag>
                        </Space>
                      }
                      description={
                        <span style={{ fontSize: 12 }}>
                          {item.back_profit !== undefined && item.back_profit !== null ? (
                            <span style={{ color: item.back_profit >= 0 ? '#52c41a' : '#ff4d4f' }}>
                              收益: {(item.back_profit * 100).toFixed(2)}%
                            </span>
                          ) : (
                            <span style={{ color: '#999' }}>运行中...</span>
                          )}
                        </span>
                      }
                    />
                  </List.Item>
                );
              }}
            />
          ) : (
            <div style={{ textAlign: 'center', padding: '20px 0', color: '#999' }}>
              暂无回测记录
            </div>
          )}
        </Card>
      )}
    </div>
  );
};

export default StrategyToolbar;

