import React, { useRef, useEffect } from 'react';
import { Card, Tag } from 'antd';
import Editor from '@monaco-editor/react';
import type { editor } from 'monaco-editor';

interface StrategyEditorProps {
  code: string;
  onChange: (value: string | undefined) => void;
  currentBacktestId?: string;
}

const defaultCode = `#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
多因子选股策略示例
"""

def init(context):
    """初始化函数"""
    # 设置股票池
    context.set_universe(['000001.SZ', '600000.SH', '000002.SZ'])
    print("策略初始化完成")

def handle_bar(context, bar_dict):
    """
    每个bar数据到来时调用
    context: 上下文对象
    bar_dict: 当前bar数据
    """
    # 获取账户信息
    account = context.stock_account
    
    # 遍历持仓
    for symbol in context.portfolio.positions.keys():
        position = context.portfolio.positions[symbol]
        print(f"持仓: {symbol}, 数量: {position.quantity}")
    
    # 示例：简单买入逻辑
    for symbol in context.universe:
        if symbol not in context.portfolio.positions:
            # 使用10%的可用资金买入
            cash = account.cash * 0.1
            if cash > 0:
                current_price = bar_dict.get(symbol, {}).get('close', 0)
                if current_price > 0:
                    amount = int(cash / current_price / 100) * 100  # 整手
                    
                    if amount >= 100:
                        order(symbol, amount)
                        print(f"买入: {symbol}, 数量: {amount}, 价格: {current_price}")

def order(symbol, amount):
    """下单函数（由框架提供）"""
    pass
`;

const StrategyEditor: React.FC<StrategyEditorProps> = ({
  code,
  onChange,
  currentBacktestId,
}) => {
  const editorRef = useRef<editor.IStandaloneCodeEditor>();

  const handleEditorDidMount = (editor: editor.IStandaloneCodeEditor) => {
    editorRef.current = editor;
  };

  return (
    <Card
      title={
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>策略代码编辑器</span>
          {currentBacktestId && <Tag color="success">回测ID: {currentBacktestId}</Tag>}
        </div>
      }
      bordered={false}
      bodyStyle={{ padding: 0, height: 'calc(100vh - 200px)' }}
    >
      <Editor
        height="100%"
        defaultLanguage="python"
        value={code}
        onChange={onChange}
        onMount={handleEditorDidMount}
        theme="vs-dark"
        options={{
          fontSize: 14,
          minimap: { enabled: true },
          automaticLayout: true,
          scrollBeyondLastLine: false,
          wordWrap: 'on',
          tabSize: 4,
        }}
      />
    </Card>
  );
};

export { defaultCode };
export default StrategyEditor;

