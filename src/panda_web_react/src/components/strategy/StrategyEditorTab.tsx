import React, { useState, useRef, useEffect } from 'react';
import { Layout, message } from 'antd';
import Editor from '@monaco-editor/react';
import type { editor } from 'monaco-editor';
import StrategyToolbar from './StrategyToolbar';
import type { BacktestConfig, BacktestRecord } from '@/types';

const { Sider, Content } = Layout;

export const defaultStrategyCode = `"""
基于研报的多因子选股策略
策略核心思路：
1. 多因子模型选股：结合价值、成长、质量、动量等多个维度
2. 定期调仓：根据因子评分重新选择股票组合
3. 风险控制：设置止损、仓位管理等风险控制措施
4. 动态调整：根据市场环境调整选股数量和仓位
"""

from panda_backtest.api.api import *
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def initialize(context):
    """
    策略初始化
    """
    SRLogger.info("=== 多因子选股策略初始化 ===")
    
    # 策略参数设置
    context.stock_account = '8888'      # 股票账户（标准账户ID）
    context.max_stocks = 10             # 最大持仓股票数量
    context.rebalance_period = 5        # 调仓周期（天）
    context.position_size = 0.08        # 单只股票仓位上限（8%）
    context.stop_loss = -0.15           # 止损线（-15%）
    context.take_profit = 0.25          # 止盈线（25%）
    
    # 股票池设置（沪深300成分股示例）
    context.stock_pool = [
        '000001.SZ', '000002.SZ', '000858.SZ', '000895.SZ', '000938.SZ',
        '000977.SZ', '002415.SZ', '002594.SZ', '002601.SZ', '002714.SZ',
        '600000.SH', '600036.SH', '600519.SH', '600887.SH', '601318.SH',
        '601398.SH', '601857.SH', '601988.SH', '600276.SH', '600309.SH'
    ]
    
    SRLogger.info(f"策略参数设置完成：最大持仓数：{context.max_stocks}")

def handle_data(context, bar_dict):
    """
    主策略逻辑
    """
    print(f"=== [{context.now}] ===\\n")
    # 在这里编写你的策略逻辑
    pass

def before_trading(context):
    """开盘前处理"""
    pass

def after_trading(context):
    """收盘后处理"""
    pass
`;

interface StrategyEditorTabProps {
  strategyId: string;
  initialCode?: string;
  initialName?: string;
  initialDescription?: string;
  defaultConfig?: BacktestConfig;
  relatedBacktests?: BacktestRecord[];
  onCodeChange: (code: string) => void;
  onSaveStrategy: (data: { name: string; description?: string; code: string }) => void;
  onStartBacktest: (config: BacktestConfig, backtestName: string, saveAsDefault: boolean, code: string, strategyName: string) => void;
  onViewBacktest: (backtestId: string) => void;
}

const StrategyEditorTab: React.FC<StrategyEditorTabProps> = ({
  strategyId,
  initialCode = defaultStrategyCode,
  initialName = '新建策略',
  initialDescription = '',
  defaultConfig,
  relatedBacktests = [],
  onCodeChange,
  onSaveStrategy,
  onStartBacktest,
  onViewBacktest,
}) => {
  const [code, setCode] = useState(initialCode);
  const [strategyName, setStrategyName] = useState(initialName);
  const [description, setDescription] = useState(initialDescription);
  const [unsavedChanges, setUnsavedChanges] = useState(strategyId === 'new');
  const [saving, setSaving] = useState(false);
  const [running, setRunning] = useState(false);

  const editorRef = useRef<editor.IStandaloneCodeEditor>();
  const initialCodeRef = useRef(initialCode);

  // 监听初始代码变化（用于加载策略时）
  useEffect(() => {
    if (initialCode !== initialCodeRef.current) {
      setCode(initialCode);
      initialCodeRef.current = initialCode;
      setUnsavedChanges(false);
    }
  }, [initialCode]);

  // 监听初始名称和描述变化
  useEffect(() => {
    setStrategyName(initialName);
    setDescription(initialDescription);
  }, [initialName, initialDescription]);

  const handleEditorDidMount = (editor: editor.IStandaloneCodeEditor) => {
    editorRef.current = editor;
  };

  const handleCodeChange = (value: string | undefined) => {
    const newCode = value || '';
    setCode(newCode);
    setUnsavedChanges(true);
    onCodeChange(newCode);
  };

  const handleUpdateStrategyInfo = (data: { name?: string; description?: string }) => {
    if (data.name !== undefined) {
      setStrategyName(data.name);
    }
    if (data.description !== undefined) {
      setDescription(data.description);
    }
    setUnsavedChanges(true);
  };

  const handleSaveStrategy = async (data: { name: string; description?: string }) => {
    setSaving(true);
    try {
      await onSaveStrategy({
        name: data.name,
        description: data.description,
        code,
      });
      setStrategyName(data.name);
      setDescription(data.description || '');
      setUnsavedChanges(false);
      initialCodeRef.current = code;
      message.success('策略保存成功');
    } catch (error: any) {
      message.error('保存失败: ' + error.message);
    } finally {
      setSaving(false);
    }
  };

  const handleStartBacktest = async (
    config: BacktestConfig,
    backtestName: string,
    saveAsDefault: boolean
  ) => {
    if (unsavedChanges) {
      message.warning('请先保存策略后再运行回测');
      return;
    }

    setRunning(true);
    try {
      await onStartBacktest(config, backtestName, saveAsDefault, code, strategyName);
      message.success('回测已启动');
    } catch (error: any) {
      message.error('启动回测失败: ' + error.message);
    } finally {
      setRunning(false);
    }
  };

  return (
    <Layout style={{ height: '100%', background: '#fff', display: 'flex', flexDirection: 'row' }}>
      <Content style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column', minHeight: 0 }}>
        <div style={{ flex: 1, padding: '16px 16px 16px 24px', display: 'flex', flexDirection: 'column', minHeight: 0 }}>
          <Editor
            height="100%"
            defaultLanguage="python"
            value={code}
            onChange={handleCodeChange}
            onMount={handleEditorDidMount}
            theme="vs-dark"
            options={{
              fontSize: 14,
              minimap: { enabled: true },
              automaticLayout: true,
              scrollBeyondLastLine: false,
              wordWrap: 'on',
              tabSize: 4,
              lineNumbers: 'on',
              renderLineHighlight: 'all',
              scrollbar: {
                vertical: 'auto',
                horizontal: 'auto',
              },
            }}
          />
        </div>
      </Content>

      <Sider
        width={360}
        style={{
          background: '#f5f5f5',
          borderLeft: '1px solid #e8e8e8',
          height: '100%',
          overflow: 'hidden',
        }}
      >
        <StrategyToolbar
          strategyId={strategyId}
          strategyName={strategyName}
          description={description}
          unsavedChanges={unsavedChanges}
          defaultConfig={defaultConfig}
          relatedBacktests={relatedBacktests}
          onSaveStrategy={handleSaveStrategy}
          onUpdateStrategyInfo={handleUpdateStrategyInfo}
          onStartBacktest={handleStartBacktest}
          onViewBacktest={onViewBacktest}
          saving={saving}
          running={running}
        />
      </Sider>
    </Layout>
  );
};

export default StrategyEditorTab;

