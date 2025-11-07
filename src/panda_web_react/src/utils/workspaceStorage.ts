/**
 * 工作区标签页持久化工具
 * 负责将标签页状态保存到 localStorage 并在页面加载时恢复
 */

import type { WorkspaceTab } from '@/types';

// localStorage 键名
const STORAGE_KEYS = {
  TABS: 'workspace_tabs',
  ACTIVE_TAB: 'workspace_active_tab',
  STRATEGY_DRAFTS: 'strategy_drafts',
  LAST_SAVE_TIME: 'workspace_last_save_time',
};

// 存储配置
const STORAGE_CONFIG = {
  MAX_TABS: 20, // 最多保存 20 个标签页
  MAX_DRAFT_SIZE: 1024 * 100, // 单个草稿最大 100KB
  MAX_TOTAL_SIZE: 1024 * 1024 * 2, // 总大小不超过 2MB
  EXPIRE_TIME: 7 * 24 * 60 * 60 * 1000, // 7天过期
};

/**
 * 检查数据是否过期
 */
function isExpired(): boolean {
  const lastSaveTime = localStorage.getItem(STORAGE_KEYS.LAST_SAVE_TIME);
  if (!lastSaveTime) return true;
  
  const elapsed = Date.now() - parseInt(lastSaveTime, 10);
  return elapsed > STORAGE_CONFIG.EXPIRE_TIME;
}

/**
 * 保存标签页列表
 */
export function saveTabs(tabs: WorkspaceTab[]): void {
  try {
    // 过滤掉不需要持久化的数据
    const tabsToSave = tabs
      .slice(0, STORAGE_CONFIG.MAX_TABS)
      .map(tab => {
        const simplifiedTab: any = {
          id: tab.id,
          type: tab.type,
          title: tab.title,
          closable: tab.closable,
        };

        // 策略标签：只保存基本信息和策略ID
        if (tab.type === 'strategy' && tab.strategyData) {
          simplifiedTab.strategyData = {
            strategyId: tab.strategyData.strategyId,
            strategyName: tab.strategyData.strategyName,
            description: tab.strategyData.description,
            unsavedChanges: tab.strategyData.unsavedChanges,
            // 代码单独存储在草稿中
          };
        }

        // 回测标签：保存回测ID和基本信息
        if (tab.type === 'backtest' && tab.backtestData) {
          simplifiedTab.backtestData = {
            backtestId: tab.backtestData.backtestId,
            backtestName: tab.backtestData.backtestName,
            status: tab.backtestData.status,
            strategyId: tab.backtestData.strategyId,
            strategyName: tab.backtestData.strategyName,
            // 不保存进度和代码快照，这些需要重新加载
          };
        }

        return simplifiedTab;
      });

    localStorage.setItem(STORAGE_KEYS.TABS, JSON.stringify(tabsToSave));
    localStorage.setItem(STORAGE_KEYS.LAST_SAVE_TIME, Date.now().toString());
    
    console.log('[WorkspaceStorage] 已保存标签页:', tabsToSave.length);
  } catch (error) {
    console.error('[WorkspaceStorage] 保存标签页失败:', error);
    // localStorage 满了，清理旧数据
    if (error instanceof Error && error.name === 'QuotaExceededError') {
      clearStorage();
    }
  }
}

/**
 * 加载标签页列表
 */
export function loadTabs(): WorkspaceTab[] | null {
  try {
    // 检查是否过期
    if (isExpired()) {
      console.log('[WorkspaceStorage] 数据已过期，清理存储');
      clearStorage();
      return null;
    }

    const savedTabs = localStorage.getItem(STORAGE_KEYS.TABS);
    if (!savedTabs) return null;

    const tabs = JSON.parse(savedTabs) as WorkspaceTab[];
    console.log('[WorkspaceStorage] 已加载标签页:', tabs.length);
    
    return tabs;
  } catch (error) {
    console.error('[WorkspaceStorage] 加载标签页失败:', error);
    return null;
  }
}

/**
 * 保存当前激活的标签页ID
 */
export function saveActiveTab(tabId: string): void {
  try {
    localStorage.setItem(STORAGE_KEYS.ACTIVE_TAB, tabId);
  } catch (error) {
    console.error('[WorkspaceStorage] 保存激活标签失败:', error);
  }
}

/**
 * 加载激活的标签页ID
 */
export function loadActiveTab(): string | null {
  try {
    if (isExpired()) return null;
    return localStorage.getItem(STORAGE_KEYS.ACTIVE_TAB);
  } catch (error) {
    console.error('[WorkspaceStorage] 加载激活标签失败:', error);
    return null;
  }
}

/**
 * 保存策略代码草稿
 */
export function saveStrategyDraft(strategyId: string, code: string, metadata?: any): void {
  try {
    // 检查单个草稿大小
    if (code.length > STORAGE_CONFIG.MAX_DRAFT_SIZE) {
      console.warn('[WorkspaceStorage] 草稿过大，不保存');
      return;
    }

    const draftsStr = localStorage.getItem(STORAGE_KEYS.STRATEGY_DRAFTS);
    const drafts = draftsStr ? JSON.parse(draftsStr) : {};

    drafts[strategyId] = {
      code,
      metadata,
      savedAt: Date.now(),
    };

    // 检查总大小
    const draftsJson = JSON.stringify(drafts);
    if (draftsJson.length > STORAGE_CONFIG.MAX_TOTAL_SIZE) {
      console.warn('[WorkspaceStorage] 草稿总大小超限，清理旧草稿');
      cleanOldDrafts(drafts);
    }

    localStorage.setItem(STORAGE_KEYS.STRATEGY_DRAFTS, JSON.stringify(drafts));
    console.log('[WorkspaceStorage] 已保存策略草稿:', strategyId);
  } catch (error) {
    console.error('[WorkspaceStorage] 保存策略草稿失败:', error);
  }
}

/**
 * 加载策略代码草稿
 */
export function loadStrategyDraft(strategyId: string): { code: string; metadata?: any } | null {
  try {
    if (isExpired()) return null;

    const draftsStr = localStorage.getItem(STORAGE_KEYS.STRATEGY_DRAFTS);
    if (!draftsStr) return null;

    const drafts = JSON.parse(draftsStr);
    const draft = drafts[strategyId];

    if (!draft) return null;

    // 检查草稿是否过期（7天）
    const elapsed = Date.now() - draft.savedAt;
    if (elapsed > STORAGE_CONFIG.EXPIRE_TIME) {
      delete drafts[strategyId];
      localStorage.setItem(STORAGE_KEYS.STRATEGY_DRAFTS, JSON.stringify(drafts));
      return null;
    }

    console.log('[WorkspaceStorage] 已加载策略草稿:', strategyId);
    return { code: draft.code, metadata: draft.metadata };
  } catch (error) {
    console.error('[WorkspaceStorage] 加载策略草稿失败:', error);
    return null;
  }
}

/**
 * 删除策略草稿
 */
export function deleteStrategyDraft(strategyId: string): void {
  try {
    const draftsStr = localStorage.getItem(STORAGE_KEYS.STRATEGY_DRAFTS);
    if (!draftsStr) return;

    const drafts = JSON.parse(draftsStr);
    delete drafts[strategyId];
    
    localStorage.setItem(STORAGE_KEYS.STRATEGY_DRAFTS, JSON.stringify(drafts));
    console.log('[WorkspaceStorage] 已删除策略草稿:', strategyId);
  } catch (error) {
    console.error('[WorkspaceStorage] 删除策略草稿失败:', error);
  }
}

/**
 * 清理旧草稿（保留最新的5个）
 */
function cleanOldDrafts(drafts: Record<string, any>): void {
  const sortedDrafts = Object.entries(drafts).sort(
    (a, b) => (b[1].savedAt || 0) - (a[1].savedAt || 0)
  );

  // 只保留最新的5个
  const cleanedDrafts: Record<string, any> = {};
  sortedDrafts.slice(0, 5).forEach(([id, draft]) => {
    cleanedDrafts[id] = draft;
  });

  localStorage.setItem(STORAGE_KEYS.STRATEGY_DRAFTS, JSON.stringify(cleanedDrafts));
}

/**
 * 清空所有存储
 */
export function clearStorage(): void {
  try {
    Object.values(STORAGE_KEYS).forEach(key => {
      localStorage.removeItem(key);
    });
    console.log('[WorkspaceStorage] 已清空所有存储');
  } catch (error) {
    console.error('[WorkspaceStorage] 清空存储失败:', error);
  }
}

/**
 * 获取存储信息（用于调试）
 */
export function getStorageInfo(): {
  tabs: number;
  drafts: number;
  totalSize: number;
  lastSaveTime: string | null;
} {
  try {
    const tabs = localStorage.getItem(STORAGE_KEYS.TABS);
    const drafts = localStorage.getItem(STORAGE_KEYS.STRATEGY_DRAFTS);
    const lastSaveTime = localStorage.getItem(STORAGE_KEYS.LAST_SAVE_TIME);

    const tabsSize = tabs ? tabs.length : 0;
    const draftsSize = drafts ? drafts.length : 0;

    return {
      tabs: tabs ? JSON.parse(tabs).length : 0,
      drafts: drafts ? Object.keys(JSON.parse(drafts)).length : 0,
      totalSize: tabsSize + draftsSize,
      lastSaveTime: lastSaveTime ? new Date(parseInt(lastSaveTime)).toLocaleString() : null,
    };
  } catch (error) {
    console.error('[WorkspaceStorage] 获取存储信息失败:', error);
    return {
      tabs: 0,
      drafts: 0,
      totalSize: 0,
      lastSaveTime: null,
    };
  }
}

