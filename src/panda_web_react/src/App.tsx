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

// 获取最近1年的日期范围（格式：YYYYMMDD）
const getLastYearDateRange = (): { start_date: string; end_date: string } => {
  return {
    start_date: '20220101',
    end_date: '20251101',
  };
};

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

  const normalizeTradeDirection = (direction: any): 'buy' | 'sell' => {
    if (typeof direction === 'string') {
      const normalized = direction.trim().toLowerCase();
      if (['buy', '买入', 'long', 'b'].includes(normalized)) {
        return 'buy';
      }
      if (['sell', '卖出', 'short', 's'].includes(normalized)) {
        return 'sell';
      }
      if (normalized === '0') return 'buy';
      if (normalized === '1') return 'buy';
      if (normalized === '-1') return 'sell';

      const parsed = Number(normalized);
      if (!Number.isNaN(parsed)) {
        if (parsed === 0) return 'buy';
        if (parsed === 1) return 'buy';
        if (parsed === -1) return 'sell';
        return parsed > 0 ? 'buy' : 'sell';
      }

      return 'sell';
    }

    if (typeof direction === 'number') {
      if (direction === 0) return 'buy';
      if (direction === 1) return 'buy';
      if (direction === -1) return 'sell';
      return direction > 0 ? 'buy' : 'sell';
    }

    return 'sell';
  };

  const mapTradeRecord = (trade: any): TradeData => ({
    date: trade.date || trade.trade_date || trade.gmt_create_time || trade.gmt_create || '',
    code: trade.code || trade.contract_code || trade.symbol || '',
    contract_name: trade.contract_name || trade.name || '',
    direction: normalizeTradeDirection(trade.direction),
    amount: trade.amount || trade.volume || 0,
    price: trade.price ? String(trade.price) : '0.00',
    cost: String(trade.cost ?? trade.amount ?? 0),
  });

  // 定时器引用
  const progressTimersRef = useRef<Record<string, ReturnType<typeof setInterval>>>({});
  const dataRefreshTimersRef = useRef<Record<string, ReturnType<typeof setInterval>>>({});
  const positionAnalysisLoadingRef = useRef<Record<string, boolean>>({});
  const tradeAnalysisLoadingRef = useRef<Record<string, boolean>>({});
  const positionAnalysisLoadedRef = useRef<Record<string, boolean>>({});
  const tradeAnalysisLoadedRef = useRef<Record<string, boolean>>({});
  const resultLoadingRef = useRef<Record<string, boolean>>({});

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
    code: string,
    strategyName: string,
    strategyId?: string
  ) => {
    try {
      // 确保 strategy_id 正确传递（不传 'new' 或 undefined）
      const validStrategyId = strategyId && strategyId !== 'new' ? strategyId : undefined;
      
      console.log('[App] 启动回测 - strategyId:', strategyId, '→ validStrategyId:', validStrategyId);
      
      const result = await backtestApi.startBacktest({
        strategy_code: code,
        strategy_name: backtestName || strategyName,
        strategy_id: validStrategyId,
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
    }, 3000);
    
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
    }, 5000);
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

      const progressStatus = (data.status || '') as string;
      if (['completed', 'failed', 'cancelled'].includes(progressStatus)) {
        // 停止进度轮询
        if (progressTimersRef.current[backtestId]) {
          clearInterval(progressTimersRef.current[backtestId]);
          delete progressTimersRef.current[backtestId];
        }
        
        // 停止数据刷新轮询
        stopDataRefreshPolling(backtestId);
        
        if (progressStatus === 'completed') {
          message.success('回测完成！');
          // 加载最终结果
          await loadBacktestResults(backtestId);
        } else if (progressStatus === 'cancelled') {
          message.warning('回测已终止');
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

  const cancelBacktest = async (backtestId: string) => {
    try {
      const result = await backtestApi.cancelBacktest(backtestId);
      if (result.success) {
        message.success(result.message || '回测终止请求已发送');
        
        // 立即更新状态
        setTabs(prevTabs => prevTabs.map(tab => {
          if (tab.type === 'backtest' && tab.backtestData?.backtestId === backtestId) {
            return {
              ...tab,
              backtestData: {
                ...tab.backtestData,
                status: 'cancelled',
              },
            };
          }
          return tab;
        }));
        
        // 停止轮询
        if (progressTimersRef.current[backtestId]) {
          clearInterval(progressTimersRef.current[backtestId]);
          delete progressTimersRef.current[backtestId];
        }
        stopDataRefreshPolling(backtestId);
        
        // 加载当前结果
        await loadBacktestResults(backtestId);
        
        // 刷新运行中的回测列表
        loadRunningBacktests();
      } else {
        message.error(result.message || '终止回测失败');
      }
    } catch (error: any) {
      message.error('终止回测失败: ' + error.message);
    }
  };

  const loadBacktestResults = async (backtestId: string) => {
    if (resultLoadingRef.current[backtestId]) {
      return;
    }

    resultLoadingRef.current[backtestId] = true;
    try {
      // 加载监控数据和回测详情
      const [monitorData, backtestDetail] = await Promise.all([
        backtestApi.getMonitorData(backtestId),
        backtestApi.getBacktestDetail(backtestId).catch(err => {
          console.warn('加载回测详情失败:', err);
          return null;
        }),
      ]);

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

        // 加载表格首屏数据
        const [tradeResult, positionResult] = await Promise.all([
          backtestApi.getTradeData(backtestId, 1, 20).catch(() => ({ items: [], total: 0 })),
          backtestApi.getPositionData(backtestId, 1, 2000).catch(() => ({ items: [], total: 0 })),
        ]);

        const positionData: PositionData[] = (positionResult.items || []).map(pos => ({
          symbol: pos.symbol || pos.contract_code || '',
          contract_code: pos.contract_code || pos.symbol || '',
          contract_name: pos.contract_name || '',
          code: pos.code || pos.symbol || '',
          volume: pos.volume || pos.position || 0,
          position: pos.position || pos.volume || 0,
          market_value: pos.market_value || 0,
          profit: pos.profit || 0,
          profit_rate: pos.profit_rate || 0,
          position_ratio: pos.position_ratio,
          date: pos.date || pos.gmt_create || '',
          gmt_create: pos.gmt_create || pos.date || '',
          avg_price: pos.avg_price || pos.cost_price,
          cost_price: pos.cost_price || pos.avg_price,
          now_price: pos.now_price || pos.current_price,
          current_price: pos.current_price || pos.now_price,
        }));

        const tradeData: TradeData[] = (tradeResult.items || []).map(mapTradeRecord);

        // 构建回测配置
        let config: BacktestConfig | undefined = undefined;
        if (backtestDetail) {
          const startCapital = backtestDetail.fund_stock ? parseFloat(backtestDetail.fund_stock) : 0;
          const commission = backtestDetail.commission ? parseFloat(backtestDetail.commission) : 1;
          const matchingType = backtestDetail.bar_match ? parseInt(backtestDetail.bar_match) : 1;

          const defaultDateRange = getLastYearDateRange();
          config = {
            start_capital: startCapital / 10000,
            start_date: backtestDetail.start_date || defaultDateRange.start_date,
            end_date: backtestDetail.end_date || defaultDateRange.end_date,
            frequency: backtestDetail.back_interval || '1d',
            commission_rate: commission,
            standard_symbol: backtestDetail.benchmark || '000001.SH',
            matching_type: matchingType,
          };
        }

        setBacktestDataCache(prev => {
          const currentCache = prev[backtestId] || {};
          const cachedTradeAnalysisData = Array.isArray(currentCache.tradeAnalysisData) && currentCache.tradeAnalysisData.length > 0
            ? currentCache.tradeAnalysisData
            : undefined;
          const cachedPositionAnalysisData = Array.isArray(currentCache.positionAnalysisData) && currentCache.positionAnalysisData.length > 0
            ? currentCache.positionAnalysisData
            : undefined;
          return {
            ...prev,
            [backtestId]: {
              ...currentCache,
              profitData,
              tradeData,
              tradeAnalysisData: cachedTradeAnalysisData || (tradeData.length > 0 ? tradeData : undefined),
              positionData,
              positionAnalysisData: cachedPositionAnalysisData || (positionData.length > 0 ? positionData : undefined),
              accountData,
              dataStats,
              status: monitorData.status,
              config,
            },
          };
        });

        const monitorStatus = (monitorData.status || '') as string;
        const isTerminal = ['completed', 'failed', 'cancelled'].includes(monitorStatus);
        if (isTerminal) {
          if (progressTimersRef.current[backtestId]) {
            clearInterval(progressTimersRef.current[backtestId]);
            delete progressTimersRef.current[backtestId];
          }
          stopDataRefreshPolling(backtestId);

          setTabs(prevTabs => prevTabs.map(tab => {
            if (tab.type === 'backtest' && tab.backtestData?.backtestId === backtestId) {
              return {
                ...tab,
                backtestData: {
                  ...tab.backtestData,
                  status: monitorStatus as 'pending' | 'running' | 'completed' | 'failed' | 'cancelled',
                  progress: monitorData.progress || tab.backtestData.progress || 0,
                },
              };
            }
            return tab;
          }));

          // 全量分析数据只在终态加载一次，避免每次刷新都全量翻页
          void loadAllTradeDataForBacktest(backtestId);
          void loadAllPositionDataForBacktest(backtestId);
        }
      }
    } catch (error: any) {
      console.error('加载回测结果失败:', error);
    } finally {
      resultLoadingRef.current[backtestId] = false;
    }
  };

const loadTradeDataForBacktest = async (backtestId: string, page: number, pageSize: number) => {
    try {
      const result = await backtestApi.getTradeData(backtestId, page, pageSize);
      
      const tradeData: TradeData[] = (result.items || []).map(mapTradeRecord);

      // 更新缓存中的交易数据
      setBacktestDataCache(prev => ({
        ...prev,
        [backtestId]: {
          ...prev[backtestId],
          tradeData,
        },
      }));
    } catch (error) {
      console.error('加载交易数据失败:', error);
      message.error('加载交易数据失败');
    }
  };

  const loadAllPositionDataForBacktest = async (backtestId: string) => {
    if (positionAnalysisLoadedRef.current[backtestId]) {
      const cachedData = backtestDataCache[backtestId]?.positionAnalysisData;
      if (Array.isArray(cachedData) && cachedData.length > 0) {
        return;
      }
      positionAnalysisLoadedRef.current[backtestId] = false;
    }

    if (positionAnalysisLoadingRef.current[backtestId]) {
      return;
    }

    positionAnalysisLoadingRef.current[backtestId] = true;
    try {
      const pageSize = 1000;
      let page = 1;
      let total = 0;
      const allItems: any[] = [];

      while (page === 1 || allItems.length < total) {
        const result = await backtestApi.getPositionData(backtestId, page, pageSize);
        const items = result.items || [];
        total = result.total || 0;

        allItems.push(...items);

        if (items.length < pageSize) {
          break;
        }
        page += 1;
      }

      if (allItems.length > 0) {
        console.info(`[PositionAnalysis] full position loaded: ${allItems.length}/${total || allItems.length}`);
      }

      const positionData: PositionData[] = allItems.map(pos => ({
        symbol: pos.symbol || pos.contract_code || '',
        contract_code: pos.contract_code || pos.symbol || '',
        contract_name: pos.contract_name || '',
        code: pos.code || pos.symbol || '',
        volume: pos.volume || pos.position || 0,
        position: pos.position || pos.volume || 0,
        market_value: pos.market_value || 0,
        profit: pos.profit || 0,
        profit_rate: pos.profit_rate || 0,
        position_ratio: pos.position_ratio,
        date: pos.date || pos.gmt_create || '',
        gmt_create: pos.gmt_create || pos.date || '',
        avg_price: pos.avg_price || pos.cost_price,
        cost_price: pos.cost_price || pos.avg_price,
        now_price: pos.now_price || pos.current_price,
        current_price: pos.current_price || pos.now_price,
      }));

      setBacktestDataCache(prev => ({
        ...prev,
        [backtestId]: {
          ...prev[backtestId],
          positionAnalysisData: positionData.length > 0 ? positionData : undefined,
        },
      }));
      if (total > 0 && allItems.length >= total) {
        positionAnalysisLoadedRef.current[backtestId] = true;
      }
    } catch (error) {
      console.error('加载仓位分析全量数据失败:', error);
    } finally {
      positionAnalysisLoadingRef.current[backtestId] = false;
    }
  };

  const loadAllTradeDataForBacktest = async (backtestId: string) => {
    if (tradeAnalysisLoadedRef.current[backtestId]) {
      const cachedData = backtestDataCache[backtestId]?.tradeAnalysisData;
      if (Array.isArray(cachedData) && cachedData.length > 0) {
        return;
      }
      tradeAnalysisLoadedRef.current[backtestId] = false;
    }

    if (tradeAnalysisLoadingRef.current[backtestId]) {
      return;
    }

    tradeAnalysisLoadingRef.current[backtestId] = true;
    try {
      const pageSize = 1000;
      let page = 1;
      let total = 0;
      const allItems: any[] = [];

      while (page === 1 || allItems.length < total) {
        const result = await backtestApi.getTradeData(backtestId, page, pageSize);
        const items = result.items || [];
        total = result.total || 0;

        allItems.push(...items);

        if (items.length < pageSize) {
          break;
        }
        page += 1;
      }

      if (allItems.length > 0) {
        console.info(`[TradeAnalysis] full trade loaded: ${allItems.length}/${total || allItems.length}`);
      }

      const tradeAnalysisData: TradeData[] = allItems.map(mapTradeRecord);

      setBacktestDataCache(prev => ({
        ...prev,
        [backtestId]: {
          ...prev[backtestId],
          tradeAnalysisData: tradeAnalysisData.length > 0 ? tradeAnalysisData : undefined,
        },
      }));
      if (total > 0 && allItems.length >= total) {
        tradeAnalysisLoadedRef.current[backtestId] = true;
      }
    } catch (error) {
      console.error('加载交易分析全量数据失败:', error);
    } finally {
      tradeAnalysisLoadingRef.current[backtestId] = false;
    }
  };

  // 按需加载持仓数据（分页）
  const loadPositionDataForBacktest = async (backtestId: string, page: number, pageSize: number) => {
    try {
      const result = await backtestApi.getPositionData(backtestId, page, pageSize);
      
      const positionData: PositionData[] = (result.items || []).map(pos => ({
        symbol: pos.symbol || pos.contract_code || '',
        contract_code: pos.contract_code || pos.symbol || '',
        contract_name: pos.contract_name || '',
        code: pos.code || pos.symbol || '',
        volume: pos.volume || pos.position || 0,
        position: pos.position || pos.volume || 0,
        market_value: pos.market_value || 0,
        profit: pos.profit || 0,
        profit_rate: pos.profit_rate || 0,
        position_ratio: pos.position_ratio,
        date: pos.date || pos.gmt_create || '',
        gmt_create: pos.gmt_create || pos.date || '',
        avg_price: pos.avg_price || pos.cost_price,
        cost_price: pos.cost_price || pos.avg_price,
        now_price: pos.now_price || pos.current_price,
        current_price: pos.current_price || pos.now_price,
      }));

      // 更新缓存中的持仓数据
      setBacktestDataCache(prev => ({
        ...prev,
        [backtestId]: {
          ...prev[backtestId],
          positionData,
        },
      }));
    } catch (error) {
      console.error('加载持仓数据失败:', error);
      message.error('加载持仓数据失败');
    }
  };

  // ==================== Tab管理函数 ====================
  
  const openStrategyTab = useCallback(async (strategyId: string) => {
    // 检查Tab是否已打开
    const existingTab = tabs.find(
      tab => tab.type === 'strategy' && tab.strategyData?.strategyId === strategyId
    );

    if (existingTab) {
      // 如果已打开，直接切换到该标签页
      setActiveTabId(existingTab.id);
      message.info('策略已在标签页中打开，已切换至该标签');
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
      // 如果已打开，直接切换到该标签页
      setActiveTabId(existingTab.id);
      message.info('回测已在标签页中打开，已切换至该标签');
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
    positionAnalysisLoadingRef.current = {};
    tradeAnalysisLoadingRef.current = {};
    positionAnalysisLoadedRef.current = {};
    tradeAnalysisLoadedRef.current = {};
    resultLoadingRef.current = {};
    
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
      delete positionAnalysisLoadingRef.current[backtestId];
      delete tradeAnalysisLoadingRef.current[backtestId];
      delete positionAnalysisLoadedRef.current[backtestId];
      delete tradeAnalysisLoadedRef.current[backtestId];
      delete resultLoadingRef.current[backtestId];
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
    const newStrategyId = result.id || result._id || strategyId;

    // 删除草稿（因为已经保存了）
    deleteStrategyDraft(strategyId);
    if (strategyId !== newStrategyId && newStrategyId) {
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
    code: string,
    strategyName: string,
    strategyId?: string
  ) => {
    await startBacktest(config, backtestName, code, strategyName, strategyId);
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
            onStartBacktest={(config, backtestName, code, strategyName) =>
              handleStartBacktest(config, backtestName, code, strategyName, tab.strategyData!.strategyId)
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
          tradeAnalysisData: [],
          positionData: [],
          positionAnalysisData: [],
          accountData: [],
          dataStats: { accountCount: 0, tradeCount: 0, positionCount: 0, profitCount: 0 },
          status: tab.backtestData.status,
          config: undefined,
        };

        // 使用真实配置，如果没有则使用默认配置
        const defaultDateRange = getLastYearDateRange();
        const backtestConfig: BacktestConfig = backtestData.config || {
          start_capital: 1000,
          start_date: defaultDateRange.start_date,
          end_date: defaultDateRange.end_date,
          frequency: '1d',
          commission_rate: 1,
          standard_symbol: '000001.SH',
          matching_type: 1,
        };

        return (
          <EnhancedBacktestResults
            backtesting={tab.backtestData.status === 'running'}
            currentBacktestId={tab.backtestData.backtestId}
            backtestProgress={tab.backtestData.progress || 0}
            backtestStatus={tab.backtestData.status}
            profitData={backtestData.profitData}
            tradeData={backtestData.tradeData}
            tradeAnalysisData={backtestData.tradeAnalysisData || backtestData.tradeData}
            positionData={backtestData.positionData}
            positionAnalysisData={backtestData.positionAnalysisData || backtestData.positionData}
            accountData={backtestData.accountData}
            dataStats={backtestData.dataStats}
            config={backtestConfig}
            strategyName={tab.backtestData.strategyName || ''}
            strategyId={tab.backtestData.strategyId}
            strategyCodeSnapshot={tab.backtestData.strategyCodeSnapshot}
            onLoadResults={() => loadBacktestResults(tab.backtestData!.backtestId)}
            onManualComplete={() => {}}
            onEditStrategy={(strategyId) => openStrategyTab(strategyId)}
            onRerunBacktest={() => {
              // TODO: 实现重新运行回测
              message.info('重新运行回测功能开发中...');
            }}
            onCancelBacktest={() => cancelBacktest(tab.backtestData!.backtestId)}
            onLoadTradeData={(page, pageSize) => loadTradeDataForBacktest(tab.backtestData!.backtestId, page, pageSize)}
            onLoadPositionData={(page, pageSize) => loadPositionDataForBacktest(tab.backtestData!.backtestId, page, pageSize)}
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

  // 计算已打开的策略ID和回测ID列表
  const openStrategyIds = tabs
    .filter(tab => tab.type === 'strategy' && tab.strategyData?.strategyId)
    .map(tab => tab.strategyData!.strategyId);

  const openBacktestIds = tabs
    .filter(tab => tab.type === 'backtest' && tab.backtestData?.backtestId)
    .map(tab => tab.backtestData!.backtestId);

  return (
    <Layout style={{ height: '100vh' }}>
      <WorkspaceHeader
        strategies={strategies}
        runningBacktests={runningBacktests}
        openStrategyIds={openStrategyIds}
        openBacktestIds={openBacktestIds}
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

