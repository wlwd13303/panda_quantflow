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
import BacktestMonitor from './components/BacktestMonitor';
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
  
  // 自动刷新控制
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [refreshInterval, setRefreshInterval] = useState(2000); // 2秒

  const progressTimerRef = useRef<NodeJS.Timeout>();
  const dataRefreshTimerRef = useRef<NodeJS.Timeout>();

  useEffect(() => {
    loadStrategies();
    return () => {
      if (progressTimerRef.current) {
        clearInterval(progressTimerRef.current);
      }
      if (dataRefreshTimerRef.current) {
        clearInterval(dataRefreshTimerRef.current);
      }
    };
  }, []);

  // 自动刷新数据（当有回测ID且启用自动刷新时）
  useEffect(() => {
    if (autoRefresh && currentBacktestId && activeTab === 'result') {
      // 立即加载一次
      loadBacktestResults(true);
      
      // 设置定时刷新
      dataRefreshTimerRef.current = setInterval(() => {
        loadBacktestResults(true);
      }, refreshInterval);
    } else {
      if (dataRefreshTimerRef.current) {
        clearInterval(dataRefreshTimerRef.current);
        dataRefreshTimerRef.current = undefined;
      }
    }

    return () => {
      if (dataRefreshTimerRef.current) {
        clearInterval(dataRefreshTimerRef.current);
      }
    };
  }, [autoRefresh, currentBacktestId, refreshInterval, activeTab]);

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
      
      // 注意：数据刷新由 autoRefresh 的 useEffect 自动处理
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
        // 回测完成后加载最终结果
        await loadBacktestResults();
      } else if (data.status === 'failed') {
        setBacktesting(false);
        message.error('回测失败: ' + (data.error || '未知错误'));
        if (progressTimerRef.current) {
          clearInterval(progressTimerRef.current);
        }
      }
      // 注意：不在这里加载数据了，数据刷新由独立的定时器控制
    } catch (error: any) {
      console.error('查询回测进度失败:', error);
    }
  };

  const loadBacktestResults = async (isRealtime = false) => {
    if (!currentBacktestId) return;

    try {
      // 优先使用监控 API，这是实时监控页面使用的方式，数据结构更完整、更可靠
      const monitorData = await backtestApi.getMonitorData(currentBacktestId);
      
      if (monitorData.success) {
        // 更新数据统计
        if (monitorData.stats) {
          setDataStats({
            accountCount: monitorData.stats.account_count || 0,
            tradeCount: monitorData.stats.trade_count || 0,
            positionCount: monitorData.stats.position_count || 0,
            profitCount: monitorData.stats.profit_count || 0,
          });
        }

        // 更新账户数据 - 从最新账户状态构建
        if (monitorData.latest_account) {
          const latestAccount: AccountData = {
            total_profit: monitorData.latest_account.total_asset || 0,
            available_funds: monitorData.latest_account.available || 0,
            market_value: monitorData.latest_account.market_value || 0,
            gmt_create: monitorData.latest_account.date || '',
          };
          setAccountData([latestAccount]);
        }

        // 更新净值曲线数据（用于收益图表）
        if (monitorData.equity_curve && monitorData.equity_curve.length > 0) {
          const mappedProfits = monitorData.equity_curve.map((point) => ({
            date: point.date || '',
            total_value: point.value || 0,
            total_profit: point.value || 0,
            csi_stock: point.value || 0,
            strategy_profit: point.value || 0,
            gmt_create_time: point.date || '',
          }));
          setProfitData(mappedProfits);
        }

        // 优先使用监控 API 的持仓和交易数据（已验证正确）
        // 监控 API 返回最近的数据，对于回测结果展示已经足够
        
        // 更新持仓数据（使用监控 API 的数据，保持字段名一致）
        if (monitorData.latest_positions && monitorData.latest_positions.length > 0) {
          // 直接使用监控 API 的数据，添加兼容字段
          const mappedPositions = monitorData.latest_positions.map((pos) => ({
            symbol: pos.symbol || '',           // 监控 API 字段
            contract_code: pos.symbol || '',    // 兼容字段
            code: pos.symbol || '',             // 兼容字段
            volume: pos.volume || 0,            // 监控 API 字段
            position: pos.volume || 0,          // 兼容字段
            market_value: pos.market_value || 0, // 监控 API 字段
            profit: pos.profit || 0,            // 监控 API 字段
            profit_rate: pos.profit_rate || 0,  // 监控 API 字段（收益率）
            date: pos.date || '',               // 监控 API 字段
            gmt_create: pos.date || '',         // 兼容字段
          })) as PositionData[];
          setPositionData(mappedPositions);
        }

        // 更新交易数据（使用监控 API 的数据）
        if (monitorData.recent_trades && monitorData.recent_trades.length > 0) {
          const mappedTrades = monitorData.recent_trades.map((trade) => ({
            date: trade.date || '',
            code: trade.symbol || '',
            direction: (trade.side === 0 || trade.direction === '买入') ? 'buy' : 'sell',
            amount: Math.abs(trade.volume || 0),
            price: trade.price ? Number(trade.price).toFixed(2) : '0.00',
            cost: trade.amount ? Math.abs(Number(trade.amount)).toFixed(2) : '0.00',
          })) as TradeData[];
          setTradeData(mappedTrades);
        }

        // 如果需要更多数据，可以异步加载详细 API（可选）
        try {
          const [tradeResult, positionResult] = await Promise.all([
            backtestApi.getTradeData(currentBacktestId, 1, 100),
            backtestApi.getPositionData(currentBacktestId, 1, 200),
          ]);

          // 如果详细 API 返回更多数据，用它替换（但需要正确映射）
          const trades = tradeResult.items || [];
          if (trades.length > (monitorData.recent_trades?.length || 0)) {
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
          }

          // 持仓数据：详细 API 可能返回历史持仓，这里只保留监控 API 的最新持仓
          // 如果需要历史持仓，可以在这里添加逻辑
          
        } catch (detailError: any) {
          // 详细 API 失败不影响，已经有监控 API 的数据了
          console.log('详细 API 调用失败（不影响显示）:', detailError);
        }

        // 监控 API 成功，数据已更新
        return;
      }
    } catch (monitorError: any) {
      console.log('监控 API 调用失败，尝试使用传统 API:', monitorError);
    }

    // 如果监控 API 失败，回退到原来的多个 API 调用方式
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
        message.error('加载回测结果失败: ' + error.message);
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
          autoRefresh={autoRefresh}
          refreshInterval={refreshInterval}
          onLoadResults={() => loadBacktestResults()}
          onManualComplete={manualCompleteBacktest}
          onConfigChange={setConfig}
          onStrategyNameChange={setStrategyName}
          onAutoRefreshChange={setAutoRefresh}
          onRefreshIntervalChange={setRefreshInterval}
        />
      ),
    },
    // {
    //   key: 'monitor',
    //   label: '实时监控',
    //   children: <BacktestMonitor initialBacktestId={currentBacktestId} />,
    // },
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

