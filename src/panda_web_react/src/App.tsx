import React, { useState, useEffect, useRef } from 'react';
import {
  Layout,
  Button,
  Space,
  Select,
  Tabs,
  Modal,
  Form,
  Input,
  message,
  Spin,
} from 'antd';
import {
  SaveOutlined,
  PlayCircleOutlined,
  LoadingOutlined,
} from '@ant-design/icons';
import StrategyEditor, { defaultCode } from './components/StrategyEditor';
import BacktestResults from './components/BacktestResults';
import EnhancedBacktestResults from './components/EnhancedBacktestResults';
import BacktestManagement from './components/BacktestManagement';
import { strategyApi, backtestApi } from './services/api';
import type {
  Strategy,
  BacktestConfig,
  ProfitData,
  TradeData,
  PositionData,
  AccountData,
  DataStats,
} from './types';
import './App.css';

const { Header, Content } = Layout;

const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState('code');
  const [code, setCode] = useState(defaultCode);
  const [strategyName, setStrategyName] = useState('我的策略');
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [selectedStrategyId, setSelectedStrategyId] = useState<string>();
  const [saving, setSaving] = useState(false);
  const [showSaveDialog, setShowSaveDialog] = useState(false);
  const [saveForm] = Form.useForm();

  const [backtesting, setBacktesting] = useState(false);
  const [currentBacktestId, setCurrentBacktestId] = useState<string>();
  const [backtestProgress, setBacktestProgress] = useState(0);
  const [backtestStatus, setBacktestStatus] = useState<'pending' | 'running' | 'completed' | 'failed'>('pending');

  const [config, setConfig] = useState<BacktestConfig>({
    start_capital: 1000,
    start_date: '20240101',
    end_date: '20240201',
    frequency: '1d',
    commission_rate: 1,
    standard_symbol: '000001.SH',
    matching_type: 1,
  });

  const [profitData, setProfitData] = useState<ProfitData[]>([]);
  const [tradeData, setTradeData] = useState<TradeData[]>([]);
  const [accountData, setAccountData] = useState<AccountData[]>([]);
  const [positionData, setPositionData] = useState<PositionData[]>([]);
  const [dataStats, setDataStats] = useState<DataStats>({
    accountCount: 0,
    tradeCount: 0,
    positionCount: 0,
    profitCount: 0,
  });

  const progressTimerRef = useRef<NodeJS.Timeout>();

  useEffect(() => {
    loadStrategies();
    return () => {
      if (progressTimerRef.current) {
        clearInterval(progressTimerRef.current);
      }
    };
  }, []);

  const loadStrategies = async () => {
    try {
      const data = await strategyApi.getStrategies();
      setStrategies(data);
    } catch (error: any) {
      console.error('加载策略列表失败:', error);
    }
  };

  const handleSaveStrategy = () => {
    saveForm.setFieldsValue({
      name: strategyName,
      description: '',
    });
    setShowSaveDialog(true);
  };

  const confirmSaveStrategy = async () => {
    try {
      const values = await saveForm.validateFields();
      setSaving(true);
      const result = await strategyApi.saveStrategy({
        name: values.name,
        code: code,
        description: values.description,
      });
      message.success('策略保存成功');
      setShowSaveDialog(false);
      await loadStrategies();
      setSelectedStrategyId(result.id || result._id);
    } catch (error: any) {
      if (error.errorFields) return; // Form validation error
      message.error('保存策略失败: ' + error.message);
    } finally {
      setSaving(false);
    }
  };

  const loadStrategy = async (strategyId: string) => {
    if (!strategyId) return;
    try {
      const strategy = await strategyApi.getStrategy(strategyId);
      setCode(strategy.code);
      setStrategyName(strategy.name);
      message.success('策略加载成功');
    } catch (error: any) {
      message.error('加载策略失败: ' + error.message);
    }
  };

  const startBacktest = async () => {
    if (!code.trim()) {
      message.warning('请先编写策略代码');
      return;
    }

    setBacktesting(true);
    setBacktestProgress(0);
    setBacktestStatus('running');
    setProfitData([]);
    setTradeData([]);
    setAccountData([]);
    setPositionData([]);

    try {
      const result = await backtestApi.startBacktest({
        strategy_code: code,
        strategy_name: strategyName,
        start_date: config.start_date,
        end_date: config.end_date,
        start_capital: config.start_capital * 10000,
        commission_rate: config.commission_rate,
        frequency: config.frequency,
        standard_symbol: config.standard_symbol,
        matching_type: config.matching_type,
        account_id: '8888',
        account_type: 0,
        slippage: 0,
        margin_rate: 1,
        start_future_capital: 10000000,
        start_fund_capital: 1000000,
      });

      setCurrentBacktestId(result.back_test_id);
      message.success('回测已启动，正在运行中...');
      setActiveTab('result');

      // 开始轮询进度
      startProgressPolling();

      // 3秒后首次加载数据
      setTimeout(() => {
        loadBacktestResults(true);
      }, 3000);
    } catch (error: any) {
      message.error('启动回测失败: ' + error.message);
      setBacktesting(false);
    }
  };

  const startProgressPolling = () => {
    if (progressTimerRef.current) {
      clearInterval(progressTimerRef.current);
    }
    progressTimerRef.current = setInterval(checkBacktestProgress, 2000);
  };

  const checkBacktestProgress = async () => {
    if (!currentBacktestId) return;

    try {
      const data = await backtestApi.getProgress(currentBacktestId);
      setBacktestProgress(data.progress || 0);
      setBacktestStatus(data.status);

      if (data.status === 'completed') {
        setBacktesting(false);
        setBacktestProgress(100);
        message.success('回测完成！');
        if (progressTimerRef.current) {
          clearInterval(progressTimerRef.current);
        }
        await loadBacktestResults();
      } else if (data.status === 'failed') {
        setBacktesting(false);
        message.error('回测失败: ' + (data.error || '未知错误'));
        if (progressTimerRef.current) {
          clearInterval(progressTimerRef.current);
        }
      } else if (data.status === 'running') {
        // 运行中也实时加载数据
        await loadBacktestResults(true);
      }
    } catch (error: any) {
      console.error('查询回测进度失败:', error);
    }
  };

  const loadBacktestResults = async (isRealtime = false) => {
    if (!currentBacktestId) return;

    try {
      // 加载账户数据
      const accountResult = await backtestApi.getAccountData(currentBacktestId);
      const accounts = accountResult.items || [];
      setAccountData(accounts);
      setDataStats((prev) => ({ ...prev, accountCount: accounts.length }));

      // 加载持仓数据
      const positionResult = await backtestApi.getPositionData(currentBacktestId);
      const positions = positionResult.items || [];
      setPositionData(positions);
      setDataStats((prev) => ({ ...prev, positionCount: positions.length }));

      // 加载收益数据
      const profitResult = await backtestApi.getProfitData(currentBacktestId);
      const profits = profitResult.items || [];
      const mappedProfits = profits.map((item) => ({
        date: item.gmt_create_time || item.gmt_create || item.date,
        total_value: item.csi_stock || item.total_value,
        total_profit: item.strategy_profit || item.total_profit,
        day_profit: item.day_profit,
        ...item,
      }));
      setProfitData(mappedProfits);
      setDataStats((prev) => ({ ...prev, profitCount: mappedProfits.length }));

      // 加载交易数据
      const tradeResult = await backtestApi.getTradeData(currentBacktestId);
      const trades = tradeResult.items || [];
      const mappedTrades = trades.map((trade: any) => ({
        date: trade.trade_date || trade.gmt_create_time || trade.date,
        code: trade.contract_code || trade.code,
        direction: trade.direction > 0 ? 'buy' : 'sell',
        amount: Math.abs(trade.volume || trade.amount || 0),
        price:
          trade.price !== null && trade.price !== undefined
            ? Number(trade.price).toFixed(2)
            : '0.00',
        cost:
          trade.cost !== null && trade.cost !== undefined
            ? Math.abs(Number(trade.cost)).toFixed(2)
            : '0.00',
      }));
      setTradeData(mappedTrades);
      setDataStats((prev) => ({ ...prev, tradeCount: mappedTrades.length }));
    } catch (error: any) {
      if (!isRealtime) {
        console.error('加载回测结果失败:', error);
      }
    }
  };

  const manualCompleteBacktest = () => {
    setBacktestStatus('completed');
    setBacktestProgress(100);
    setBacktesting(false);
    if (progressTimerRef.current) {
      clearInterval(progressTimerRef.current);
    }
    message.info('已手动标记为完成，正在加载结果...');
    loadBacktestResults();
  };

  const handleViewBacktest = (backId: string) => {
    setCurrentBacktestId(backId);
    setActiveTab('result');
    loadBacktestResults();
  };

  const tabItems = [
    {
      key: 'code',
      label: '策略代码',
      children: (
        <StrategyEditor
          code={code}
          onChange={(value) => setCode(value || '')}
          currentBacktestId={currentBacktestId}
        />
      ),
    },
    {
      key: 'result',
      label: '回测结果',
      children: (
        <EnhancedBacktestResults
          backtesting={backtesting}
          currentBacktestId={currentBacktestId}
          backtestProgress={backtestProgress}
          backtestStatus={backtestStatus}
          profitData={profitData}
          tradeData={tradeData}
          positionData={positionData}
          accountData={accountData}
          dataStats={dataStats}
          config={config}
          strategyName={strategyName}
          onLoadResults={() => loadBacktestResults()}
          onManualComplete={manualCompleteBacktest}
          onConfigChange={setConfig}
          onStrategyNameChange={setStrategyName}
        />
      ),
    },
    {
      key: 'management',
      label: '回测管理',
      children: <BacktestManagement onViewBacktest={handleViewBacktest} />,
    },
  ];

  return (
    <Layout style={{ height: '100vh' }}>
      <Header style={{ background: '#fff', padding: '0 20px', borderBottom: '1px solid #e4e7ed' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Space>
            <h2 style={{ margin: 0 }}>策略回测平台 - PandaAI QuantFlow</h2>
          </Space>
          <Space>
            <Button icon={<SaveOutlined />} onClick={handleSaveStrategy} loading={saving}>
              保存策略
            </Button>
            <Select
              placeholder="选择已保存的策略"
              value={selectedStrategyId}
              onChange={(value) => {
                setSelectedStrategyId(value);
                loadStrategy(value);
              }}
              allowClear
              style={{ width: 250 }}
            >
              {strategies.map((s) => (
                <Select.Option key={s.id || s._id} value={s.id || s._id || ''}>
                  {s.name}
                </Select.Option>
              ))}
            </Select>
            <Button
              type="primary"
              icon={backtesting ? <LoadingOutlined /> : <PlayCircleOutlined />}
              onClick={startBacktest}
              loading={backtesting}
              disabled={backtesting}
            >
              {backtesting ? '回测运行中...' : '开始回测'}
            </Button>
          </Space>
        </div>
      </Header>
      <Content style={{ padding: '15px', overflow: 'hidden' }}>
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          type="card"
          items={tabItems}
          style={{ height: '100%' }}
        />
      </Content>

      {/* 保存策略对话框 */}
      <Modal
        title="保存策略"
        open={showSaveDialog}
        onOk={confirmSaveStrategy}
        onCancel={() => setShowSaveDialog(false)}
        confirmLoading={saving}
        okText="确定"
        cancelText="取消"
      >
        <Form form={saveForm} layout="vertical">
          <Form.Item
            label="策略名称"
            name="name"
            rules={[{ required: true, message: '请输入策略名称' }]}
          >
            <Input placeholder="请输入策略名称" />
          </Form.Item>
          <Form.Item label="策略描述" name="description">
            <Input.TextArea rows={3} placeholder="请输入策略描述（可选）" />
          </Form.Item>
        </Form>
      </Modal>
    </Layout>
  );
};

export default App;

