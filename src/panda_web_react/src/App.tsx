import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Layout, message } from 'antd';
import WorkspaceHeader from './components/workspace/WorkspaceHeader';
import WorkspaceTabs from './components/workspace/WorkspaceTabs';
import StrategyEditorTab, { defaultStrategyCode } from './components/strategy/StrategyEditorTab';
import EnhancedBacktestResults from './components/EnhancedBacktestResults';
import ManagementCenter from './components/management/ManagementCenter';
import { strategyApi, backtestApi } from './services/api';
import {
  saveTabs,
  loadTabs,
  saveActiveTab,
  loadActiveTab,
  saveStrategyDraft,
  loadStrategyDraft,
  deleteStrategyDraft,
  clearStorage,
} from './utils/workspaceStorage';
import type {
  Strategy,
  BacktestConfig,
  BacktestRecord,
  WorkspaceTab,
  ProfitData,
  TradeData,
  PositionData,
  AccountData,
  DataStats,
} from './types';
import './App.css';

const { Content } = Layout;

// 生成回测标签页名称的辅助函数
const generateBacktestTabName = (record: BacktestRecord): string => {
  let tabName = record.strategy_name || '';
  
  // 如果策略名称为空或只是数字，使用更有意义的名称
  if (!tabName || /^\d+$/.test(tabName.trim())) {
    if (record.start_date && record.end_date) {
      // 格式化日期，如果是标准的 YYYYMMDD 格式，转换为更友好的格式
      const formatDate = (dateStr: string) => {
        if (dateStr.length === 8 && /^\d{8}$/.test(dateStr)) {
          return `${dateStr.substring(0, 4)}-${dateStr.substring(4, 6)}-${dateStr.substring(6, 8)}`;
        }
        return dateStr;
      };
      
      const startDate = formatDate(record.start_date);
      const endDate = formatDate(record.end_date);
      tabName = `回测 ${startDate}~${endDate}`;
    } else {
      const shortId = (record.run_id || record._id || '').substring(0, 8);
      tabName = `回测 ${shortId}`;
    }
  }
  
  return tabName;
};

const App: React.FC = () => {
  // ==================== 状态管理 ====================
  
  // Tab管理
  const [tabs, setTabs] = useState<WorkspaceTab[]>([
    {
      id: 'management',
      type: 'management',
      title: '管理中心',
      closable: false,
    },
  ]);
  const [activeTabId, setActiveTabId] = useState('management');
  const [workspaceRestored, setWorkspaceRestored] = useState(false);

  // 策略列表
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [strategiesLoading, setStrategiesLoading] = useState(false);

  // 运行中的回测
  const [runningBacktests, setRunningBacktests] = useState<BacktestRecord[]>([]);

  // 回测数据缓存（按backtestId存储）
  const [backtestDataCache, setBacktestDataCache] = useState<Record<string, any>>({});

  // 定时器引用
  const progressTimersRef = useRef<Record<string, NodeJS.Timeout>>({});
  const dataRefreshTimersRef = useRef<Record<string, NodeJS.Timeout>>({});

  // ==================== 初始化 ====================
  
  // 恢复工作区状态
  useEffect(() => {
    const restoreWorkspace = async () => {
      console.log('[App] 开始恢复工作区...');
      
      // 加载策略列表（必须先加载，后续需要用到）
      await loadStrategies();
      await loadRunningBacktests();

      // 尝试从 localStorage 恢复标签页
      const savedTabs = loadTabs();
      const savedActiveTab = loadActiveTab();

      if (savedTabs && savedTabs.length > 0) {
        console.log('[App] 恢复标签页:', savedTabs.length);
        
        // 确保管理中心标签存在
        const hasManagementTab = savedTabs.some(tab => tab.type === 'management');
        const restoredTabs: WorkspaceTab[] = hasManagementTab
          ? savedTabs
          : [
              {
                id: 'management',
                type: 'management',
                title: '管理中心',
                closable: false,
              },
              ...savedTabs,
            ];

        // 恢复策略标签的代码（从草稿或重新加载）
        const tabsWithData = await Promise.all(
          restoredTabs.map(async (tab) => {
            if (tab.type === 'strategy' && tab.strategyData) {
              // 尝试加载草稿
              const draft = loadStrategyDraft(tab.strategyData.strategyId);
              
              if (draft && draft.code) {
                // 使用草稿代码
                console.log('[App] 使用草稿代码:', tab.strategyData.strategyId);
                return {
                  ...tab,
                  strategyData: {
                    ...tab.strategyData,
                    code: draft.code,
                    unsavedChanges: true,
                  },
                };
              } else if (tab.strategyData.strategyId !== 'new') {
                // 重新加载策略代码
                const strategy = await loadStrategy(tab.strategyData.strategyId);
                if (strategy) {
                  console.log('[App] 重新加载策略:', tab.strategyData.strategyId);
                  return {
                    ...tab,
                    strategyData: {
                      ...tab.strategyData,
                      code: strategy.code,
                      description: strategy.description,
                      unsavedChanges: false,
                      defaultConfig: strategy.default_backtest_config,
                    },
                  };
                }
              } else {
                // 新建策略，使用默认代码
                return {
                  ...tab,
                  strategyData: {
                    ...tab.strategyData,
                    code: defaultStrategyCode,
                    unsavedChanges: true,
                  },
                };
              }
            }

            if (tab.type === 'backtest' && tab.backtestData) {
              // 回测标签需要重新加载状态
              const backtestId = tab.backtestData.backtestId;
              
              // 重新开始轮询（如果是运行中的回测）
              if (tab.backtestData.status === 'running') {
                startProgressPolling(backtestId); // 这会自动启动数据刷新
              } else if (tab.backtestData.status === 'completed') {
                // 重新加载完成的回测结果
                loadBacktestResults(backtestId);
              }
            }

            return tab;
          })
        );

        setTabs(tabsWithData);

        // 恢复激活的标签
        if (savedActiveTab && tabsWithData.some(t => t.id === savedActiveTab)) {
          setActiveTabId(savedActiveTab);
        } else if (tabsWithData.length > 0) {
          setActiveTabId(tabsWithData[0].id);
        }

        message.success('工作区已恢复');
      }

      setWorkspaceRestored(true);
    };

    restoreWorkspace();

    // 清理定时器
    return () => {
      Object.values(progressTimersRef.current).forEach(clearInterval);
      Object.values(dataRefreshTimersRef.current).forEach(clearInterval);
    };
  }, []);

  // 保存标签页状态到 localStorage
  useEffect(() => {
    if (!workspaceRestored) return; // 等待恢复完成后再保存
    
    saveTabs(tabs);
    console.log('[App] 已保存标签页状态');
  }, [tabs, workspaceRestored]);

  // 保存激活的标签页
  useEffect(() => {
    if (!workspaceRestored) return;
    
    saveActiveTab(activeTabId);
    console.log('[App] 已保存激活标签:', activeTabId);
  }, [activeTabId, workspaceRestored]);

  // ==================== 策略相关函数 ====================
  
  const loadStrategies = async () => {
    setStrategiesLoading(true);
    try {
      const data = await strategyApi.getStrategies();
      setStrategies(data);
    } catch (error: any) {
      console.error('加载策略列表失败:', error);
      message.error('加载策略列表失败: ' + error.message);
    } finally {
      setStrategiesLoading(false);
    }
  };

  const loadStrategy = async (strategyId: string): Promise<Strategy | null> => {
    try {
      const strategy = await strategyApi.getStrategy(strategyId);
      return strategy;
    } catch (error: any) {
      message.error('加载策略失败: ' + error.message);
      return null;
    }
  };

  const saveStrategy = async (data: { name: string; description?: string; code: string }, strategyId?: string) => {
    try {
      const result = await strategyApi.saveStrategy({
        id: strategyId !== 'new' ? strategyId : undefined,
        name: data.name,
        code: data.code,
        description: data.description,
      });
      
      await loadStrategies();
      return result;
    } catch (error: any) {
      throw new Error('保存策略失败: ' + error.message);
    }
  };

  const deleteStrategy = async (strategyId: string) => {
    try {
      await strategyApi.deleteStrategy(strategyId);
      await loadStrategies();
    } catch (error: any) {
      throw new Error('删除策略失败: ' + error.message);
    }
  };

  // ==================== 回测相关函数 ====================
  
  const loadRunningBacktests = async () => {
    try {
      const result = await backtestApi.getBacktestList(1, 100, 'running');
      setRunningBacktests(result.items || []);
    } catch (error: any) {
      console.error('加载运行中的回测失败:', error);
    }
  };

  const startBacktest = async (
    config: BacktestConfig,
    backtestName: string,
    saveAsDefault: boolean,
    code: string,
    strategyName: string,
    strategyId?: string
  ) => {
    try {
      const result = await backtestApi.startBacktest({
        strategy_code: code,
        strategy_name: backtestName || strategyName,
        strategy_id: strategyId !== 'new' ? strategyId : undefined,
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

      const backtestId = result.back_test_id;
      
      // 打开回测结果Tab，传递代码快照
      openBacktestTab(backtestId, backtestName || strategyName, strategyId, code);
      
      // 刷新运行中的回测列表
      loadRunningBacktests();
      
      // 开始轮询进度
      startProgressPolling(backtestId);
      
      return backtestId;
    } catch (error: any) {
      throw new Error('启动回测失败: ' + error.message);
    }
  };

  const startProgressPolling = (backtestId: string) => {
    if (progressTimersRef.current[backtestId]) {
      clearInterval(progressTimersRef.current[backtestId]);
    }
    
    progressTimersRef.current[backtestId] = setInterval(() => {
      checkBacktestProgress(backtestId);
    }, 2000);
    
    // 同时启动数据刷新定时器，实时加载回测数据
    startDataRefreshPolling(backtestId);
  };

  const startDataRefreshPolling = (backtestId: string) => {
    if (dataRefreshTimersRef.current[backtestId]) {
      clearInterval(dataRefreshTimersRef.current[backtestId]);
    }
    
    // 立即加载一次数据
    loadBacktestResults(backtestId);
    
    // 每2秒刷新一次回测数据
    dataRefreshTimersRef.current[backtestId] = setInterval(() => {
      loadBacktestResults(backtestId);
    }, 2000);
  };

  const stopDataRefreshPolling = (backtestId: string) => {
    if (dataRefreshTimersRef.current[backtestId]) {
      clearInterval(dataRefreshTimersRef.current[backtestId]);
      delete dataRefreshTimersRef.current[backtestId];
    }
  };

  const checkBacktestProgress = async (backtestId: string) => {
    try {
      const data = await backtestApi.getProgress(backtestId);
      
      // 更新对应Tab的状态
      setTabs(prevTabs => prevTabs.map(tab => {
        if (tab.type === 'backtest' && tab.backtestData?.backtestId === backtestId) {
          return {
            ...tab,
            backtestData: {
              ...tab.backtestData,
              status: data.status,
              progress: data.progress || 0,
            },
          };
        }
        return tab;
      }));

      if (data.status === 'completed' || data.status === 'failed') {
        // 停止进度轮询
        if (progressTimersRef.current[backtestId]) {
          clearInterval(progressTimersRef.current[backtestId]);
          delete progressTimersRef.current[backtestId];
        }
        
        // 停止数据刷新轮询
        stopDataRefreshPolling(backtestId);
        
        if (data.status === 'completed') {
          message.success('回测完成！');
          // 加载最终结果
          await loadBacktestResults(backtestId);
        } else {
          message.error('回测失败: ' + (data.error || '未知错误'));
        }
        
        // 刷新运行中的回测列表
        loadRunningBacktests();
      }
    } catch (error: any) {
      console.error('查询回测进度失败:', error);
    }
  };

  const loadBacktestResults = async (backtestId: string) => {
    try {
      // 使用监控 API
      const monitorData = await backtestApi.getMonitorData(backtestId);

      if (monitorData.success) {
        const dataStats: DataStats = {
          accountCount: monitorData.stats?.account_count || 0,
          tradeCount: monitorData.stats?.trade_count || 0,
          positionCount: monitorData.stats?.position_count || 0,
          profitCount: monitorData.stats?.profit_count || 0,
        };

        const accountData: AccountData[] = monitorData.latest_account ? [{
          total_profit: monitorData.latest_account.total_asset || 0,
          available_funds: monitorData.latest_account.available || 0,
          market_value: monitorData.latest_account.market_value || 0,
          gmt_create: monitorData.latest_account.date || '',
        }] : [];

        const profitData: ProfitData[] = (monitorData.equity_curve || []).map(point => ({
          date: point.date || '',
          total_value: point.value || 0,
          total_profit: point.value || 0,
          csi_stock: point.value || 0,
          strategy_profit: point.value || 0,
          gmt_create_time: point.date || '',
        }));

        const positionData: PositionData[] = (monitorData.latest_positions || []).map(pos => ({
          symbol: pos.symbol || '',
          contract_code: pos.symbol || '',
          code: pos.symbol || '',
          volume: pos.volume || 0,
          position: pos.volume || 0,
          market_value: pos.market_value || 0,
          profit: pos.profit || 0,
          profit_rate: pos.profit_rate || 0,
          date: pos.date || '',
          gmt_create: pos.date || '',
        }));

        const tradeData: TradeData[] = (monitorData.recent_trades || []).map(trade => ({
          date: trade.date || '',
          code: trade.symbol || '',
          direction: (trade.side === 0 || trade.direction === '买入') ? 'buy' : 'sell',
          amount: Math.abs(trade.volume || 0),
          price: trade.price ? Number(trade.price).toFixed(2) : '0.00',
          cost: trade.amount ? Math.abs(Number(trade.amount)).toFixed(2) : '0.00',
        }));

        // 缓存数据
        setBacktestDataCache(prev => ({
          ...prev,
          [backtestId]: {
            profitData,
            tradeData,
            positionData,
            accountData,
            dataStats,
            status: monitorData.status,
          },
        }));
      }
    } catch (error: any) {
      console.error('加载回测结果失败:', error);
    }
  };

  // ==================== Tab管理函数 ====================
  
  const openStrategyTab = useCallback(async (strategyId: string) => {
    // 检查Tab是否已打开
    const existingTab = tabs.find(
      tab => tab.type === 'strategy' && tab.strategyData?.strategyId === strategyId
    );

    if (existingTab) {
      setActiveTabId(existingTab.id);
      return;
    }

    // 加载策略数据
    let strategy: Strategy | null = null;
    let code = defaultStrategyCode;
    let name = '新建策略';
    let description = '';

    if (strategyId !== 'new') {
      strategy = await loadStrategy(strategyId);
      if (strategy) {
        code = strategy.code;
        name = strategy.name;
        description = strategy.description || '';
      }
    }

    // 创建新Tab
    const newTab: WorkspaceTab = {
      id: `strategy-${strategyId}-${Date.now()}`,
      type: 'strategy',
      title: name,
      closable: true,
      strategyData: {
        strategyId,
        strategyName: name,
        code,
        description,
        unsavedChanges: strategyId === 'new',
        defaultConfig: strategy?.default_backtest_config,
      },
    };

    setTabs(prev => [...prev, newTab]);
    setActiveTabId(newTab.id);
  }, [tabs]);

  const openBacktestTab = useCallback((
    backtestId: string,
    backtestName: string,
    strategyId?: string,
    strategyCodeSnapshot?: string
  ) => {
    // 检查Tab是否已打开
    const existingTab = tabs.find(
      tab => tab.type === 'backtest' && tab.backtestData?.backtestId === backtestId
    );

    if (existingTab) {
      setActiveTabId(existingTab.id);
      return;
    }

    // 创建新Tab
    const newTab: WorkspaceTab = {
      id: `backtest-${backtestId}-${Date.now()}`,
      type: 'backtest',
      title: backtestName,
      closable: true,
      backtestData: {
        backtestId,
        backtestName,
        status: 'running',
        progress: 0,
        strategyId,
        strategyName: backtestName,
        strategyCodeSnapshot,
      },
    };

    setTabs(prev => [...prev, newTab]);
    setActiveTabId(newTab.id);
  }, [tabs]);

  const openManagementTab = useCallback(() => {
    const managementTab = tabs.find(tab => tab.type === 'management');
    if (managementTab) {
      setActiveTabId(managementTab.id);
    }
  }, [tabs]);

  const handleClearWorkspace = useCallback(() => {
    // 清空 localStorage
    clearStorage();
    
    // 停止所有定时器
    Object.values(progressTimersRef.current).forEach(clearInterval);
    Object.values(dataRefreshTimersRef.current).forEach(clearInterval);
    progressTimersRef.current = {};
    dataRefreshTimersRef.current = {};
    
    // 重置为初始状态（只保留管理中心）
    setTabs([
      {
        id: 'management',
        type: 'management',
        title: '管理中心',
        closable: false,
      },
    ]);
    setActiveTabId('management');
    
    message.success('工作区已清空');
  }, []);

  const closeTab = useCallback((tabId: string) => {
    const tab = tabs.find(t => t.id === tabId);
    if (!tab || !tab.closable) return;

    // 如果是策略Tab，删除对应的草稿（除非有未保存的修改）
    if (tab.type === 'strategy' && tab.strategyData) {
      // 只有在没有未保存修改时才删除草稿
      if (!tab.strategyData.unsavedChanges) {
        deleteStrategyDraft(tab.strategyData.strategyId);
      }
    }

    // 如果是回测Tab，停止相关定时器
    if (tab.type === 'backtest' && tab.backtestData) {
      const backtestId = tab.backtestData.backtestId;
      if (progressTimersRef.current[backtestId]) {
        clearInterval(progressTimersRef.current[backtestId]);
        delete progressTimersRef.current[backtestId];
      }
      if (dataRefreshTimersRef.current[backtestId]) {
        clearInterval(dataRefreshTimersRef.current[backtestId]);
        delete dataRefreshTimersRef.current[backtestId];
      }
    }

    // 移除Tab
    const newTabs = tabs.filter(t => t.id !== tabId);
    setTabs(newTabs);

    // 如果关闭的是当前Tab，切换到管理中心
    if (activeTabId === tabId) {
      const managementTab = newTabs.find(t => t.type === 'management');
      if (managementTab) {
        setActiveTabId(managementTab.id);
      }
    }
  }, [tabs, activeTabId]);

  // ==================== 策略操作回调 ====================
  
  const handleSaveStrategy = async (
    data: { name: string; description?: string; code: string },
    strategyId: string,
    tabId: string
  ) => {
    const result = await saveStrategy(data, strategyId);
    const newStrategyId = result.id || result._id;

    // 删除草稿（因为已经保存了）
    deleteStrategyDraft(strategyId);
    if (strategyId !== newStrategyId) {
      deleteStrategyDraft(newStrategyId);
    }

    // 更新Tab
    setTabs(prevTabs => prevTabs.map(tab => {
      if (tab.id === tabId && tab.strategyData) {
        return {
          ...tab,
          title: data.name,
          strategyData: {
            ...tab.strategyData,
            strategyId: newStrategyId,
            strategyName: data.name,
            code: data.code,
            description: data.description,
            unsavedChanges: false,
          },
        };
      }
      return tab;
    }));
  };

  const handleStartBacktest = async (
    config: BacktestConfig,
    backtestName: string,
    saveAsDefault: boolean,
    code: string,
    strategyName: string,
    strategyId?: string
  ) => {
    await startBacktest(config, backtestName, saveAsDefault, code, strategyName, strategyId);
  };

  const handleCodeChange = (code: string, tabId: string) => {
    setTabs(prevTabs => prevTabs.map(tab => {
      if (tab.id === tabId && tab.strategyData) {
        // 保存草稿到 localStorage
        saveStrategyDraft(tab.strategyData.strategyId, code, {
          strategyName: tab.strategyData.strategyName,
          description: tab.strategyData.description,
        });
        
        return {
          ...tab,
          strategyData: {
            ...tab.strategyData,
            code,
            unsavedChanges: true,
          },
        };
      }
      return tab;
    }));
  };

  // ==================== 渲染Tab内容 ====================
  
  const renderTabContent = (tab: WorkspaceTab) => {
    switch (tab.type) {
      case 'strategy':
        if (!tab.strategyData) return null;
        
        return (
          <StrategyEditorTab
            strategyId={tab.strategyData.strategyId}
            initialCode={tab.strategyData.code}
            initialName={tab.strategyData.strategyName}
            initialDescription={tab.strategyData.description}
            defaultConfig={tab.strategyData.defaultConfig}
            relatedBacktests={[]}
            onCodeChange={(code) => handleCodeChange(code, tab.id)}
            onSaveStrategy={(data) => handleSaveStrategy(data, tab.strategyData!.strategyId, tab.id)}
            onStartBacktest={(config, backtestName, saveAsDefault, code, strategyName) =>
              handleStartBacktest(config, backtestName, saveAsDefault, code, strategyName, tab.strategyData!.strategyId)
            }
            onViewBacktest={(backtestId) => {
              const shortId = backtestId.substring(0, 8);
              openBacktestTab(backtestId, `回测 ${shortId}`, tab.strategyData?.strategyId);
            }}
          />
        );

      case 'backtest':
        if (!tab.backtestData) return null;
        
        const backtestData = backtestDataCache[tab.backtestData.backtestId] || {
          profitData: [],
          tradeData: [],
          positionData: [],
          accountData: [],
          dataStats: { accountCount: 0, tradeCount: 0, positionCount: 0, profitCount: 0 },
          status: tab.backtestData.status,
        };

        return (
          <EnhancedBacktestResults
            backtesting={tab.backtestData.status === 'running'}
            currentBacktestId={tab.backtestData.backtestId}
            backtestProgress={tab.backtestData.progress || 0}
            backtestStatus={tab.backtestData.status}
            profitData={backtestData.profitData}
            tradeData={backtestData.tradeData}
            positionData={backtestData.positionData}
            accountData={backtestData.accountData}
            dataStats={backtestData.dataStats}
            config={{
              start_capital: 1000,
              start_date: '20240101',
              end_date: '20240201',
              frequency: '1d',
              commission_rate: 1,
              standard_symbol: '000001.SH',
              matching_type: 1,
            }}
            strategyName={tab.backtestData.strategyName || ''}
            strategyId={tab.backtestData.strategyId}
            strategyCodeSnapshot={tab.backtestData.strategyCodeSnapshot}
            onLoadResults={() => loadBacktestResults(tab.backtestData!.backtestId)}
            onManualComplete={() => {}}
            onEditStrategy={(strategyId) => openStrategyTab(strategyId)}
            onRerunBacktest={(config) => {
              // TODO: 实现重新运行回测
              message.info('重新运行回测功能开发中...');
            }}
          />
        );

      case 'management':
        return (
          <ManagementCenter
            strategies={strategies}
            strategiesLoading={strategiesLoading}
            onEditStrategy={openStrategyTab}
            onDeleteStrategy={deleteStrategy}
            onNewStrategy={() => openStrategyTab('new')}
            onRefreshStrategies={loadStrategies}
            onViewBacktest={(backtestId, record) => {
              const tabName = generateBacktestTabName(record);
              openBacktestTab(
                backtestId,
                tabName,
                record.strategy_id,
                record.strategy_code_snapshot
              );
            }}
          />
        );

      default:
        return null;
    }
  };

  // ==================== 渲染 ====================
  
  const currentTab = tabs.find(t => t.id === activeTabId);

  return (
    <Layout style={{ height: '100vh' }}>
      <WorkspaceHeader
        strategies={strategies}
        runningBacktests={runningBacktests}
        onNewStrategy={() => openStrategyTab('new')}
        onOpenStrategy={openStrategyTab}
        onOpenBacktest={(backtestId) => {
          // 从 runningBacktests 中找到对应的记录
          const record = runningBacktests.find(
            bt => (bt.run_id || bt._id) === backtestId
          );
          
          if (record) {
            const tabName = generateBacktestTabName(record);
            openBacktestTab(
              backtestId,
              tabName,
              record.strategy_id,
              record.strategy_code_snapshot
            );
          } else {
            // 如果找不到记录，使用默认名称
            openBacktestTab(backtestId, `回测 ${backtestId.substring(0, 8)}`);
          }
        }}
        onOpenManagement={openManagementTab}
        onClearWorkspace={handleClearWorkspace}
      />

      <Layout style={{ height: 'calc(100vh - 64px)', display: 'flex', flexDirection: 'column' }}>
        <WorkspaceTabs
          tabs={tabs}
          activeTabId={activeTabId}
          onTabChange={setActiveTabId}
          onTabClose={closeTab}
        />

        <Content style={{ 
          background: '#f5f5f5', 
          overflow: 'hidden',
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          minHeight: 0
        }}>
          {currentTab && renderTabContent(currentTab)}
        </Content>
      </Layout>
    </Layout>
  );
};

export default App;

