import React, { useMemo } from 'react';
import { Modal, Tabs, Alert, Space, Button } from 'antd';
import Editor from '@monaco-editor/react';

interface CodeDiffViewerProps {
  visible: boolean;
  oldCode: string;
  newCode: string;
  oldTitle?: string;
  newTitle?: string;
  onClose: () => void;
}

// 简单的逐行对比函数
const diffLines = (oldCode: string, newCode: string) => {
  const oldLines = oldCode.split('\n');
  const newLines = newCode.split('\n');
  const maxLines = Math.max(oldLines.length, newLines.length);
  const diff: Array<{ old?: string; new?: string; type: 'equal' | 'added' | 'removed' | 'modified' }> = [];

  // 简单的逐行对比
  for (let i = 0; i < maxLines; i++) {
    const oldLine = oldLines[i];
    const newLine = newLines[i];

    if (oldLine === undefined) {
      diff.push({ new: newLine, type: 'added' });
    } else if (newLine === undefined) {
      diff.push({ old: oldLine, type: 'removed' });
    } else if (oldLine === newLine) {
      diff.push({ old: oldLine, new: newLine, type: 'equal' });
    } else {
      diff.push({ old: oldLine, new: newLine, type: 'modified' });
    }
  }

  return diff;
};

const CodeDiffViewer: React.FC<CodeDiffViewerProps> = ({
  visible,
  oldCode,
  newCode,
  oldTitle = '原始代码',
  newTitle = '当前代码',
  onClose,
}) => {
  const diff = useMemo(() => diffLines(oldCode, newCode), [oldCode, newCode]);
  
  const addedCount = diff.filter(d => d.type === 'added').length;
  const removedCount = diff.filter(d => d.type === 'removed').length;
  const modifiedCount = diff.filter(d => d.type === 'modified').length;
  const hasChanges = addedCount > 0 || removedCount > 0 || modifiedCount > 0;

  // 生成带标记的代码（用于并排对比）
  const generateMarkedCode = (side: 'old' | 'new') => {
    return diff.map((item, index) => {
      const line = side === 'old' ? item.old : item.new;
      if (line === undefined) return '';
      
      let prefix = '';
      if (item.type === 'added' && side === 'new') {
        prefix = '+ ';
      } else if (item.type === 'removed' && side === 'old') {
        prefix = '- ';
      } else if (item.type === 'modified') {
        prefix = side === 'old' ? '- ' : '+ ';
      } else {
        prefix = '  ';
      }
      
      return `${prefix}${line}`;
    }).join('\n');
  };

  const oldMarkedCode = generateMarkedCode('old');
  const newMarkedCode = generateMarkedCode('new');

  const tabItems = [
    {
      key: 'side-by-side',
      label: '并排对比',
      children: (
        <div style={{ display: 'flex', gap: 8, height: 600 }}>
          <div style={{ flex: 1, border: '1px solid #d9d9d9', borderRadius: 4 }}>
            <div style={{ 
              padding: '8px 12px', 
              background: '#f5f5f5', 
              borderBottom: '1px solid #d9d9d9',
              fontWeight: 500,
              fontSize: 13
            }}>
              {oldTitle}
            </div>
            <Editor
              height="calc(100% - 40px)"
              language="python"
              value={oldMarkedCode}
              options={{
                readOnly: true,
                minimap: { enabled: false },
                scrollBeyondLastLine: false,
                wordWrap: 'on',
                lineNumbers: 'on',
                renderLineHighlight: 'all',
                lineDecorationsWidth: 4,
                lineNumbersMinChars: 3,
                glyphMargin: false,
                folding: true,
                scrollbar: {
                  vertical: 'auto',
                  horizontal: 'auto',
                },
              }}
              theme="vs-dark"
            />
          </div>
          <div style={{ flex: 1, border: '1px solid #d9d9d9', borderRadius: 4 }}>
            <div style={{ 
              padding: '8px 12px', 
              background: '#f5f5f5', 
              borderBottom: '1px solid #d9d9d9',
              fontWeight: 500,
              fontSize: 13
            }}>
              {newTitle}
            </div>
            <Editor
              height="calc(100% - 40px)"
              language="python"
              value={newMarkedCode}
              options={{
                readOnly: true,
                minimap: { enabled: false },
                scrollBeyondLastLine: false,
                wordWrap: 'on',
                lineNumbers: 'on',
                renderLineHighlight: 'all',
                lineDecorationsWidth: 4,
                lineNumbersMinChars: 3,
                glyphMargin: false,
                folding: true,
                scrollbar: {
                  vertical: 'auto',
                  horizontal: 'auto',
                },
              }}
              theme="vs-dark"
            />
          </div>
        </div>
      ),
    },
    {
      key: 'old',
      label: oldTitle,
      children: (
        <div style={{ height: 600 }}>
          <Editor
            height="100%"
            language="python"
            value={oldCode}
            options={{
              readOnly: true,
              minimap: { enabled: true },
              scrollBeyondLastLine: false,
              wordWrap: 'on',
            }}
            theme="vs-dark"
          />
        </div>
      ),
    },
    {
      key: 'new',
      label: newTitle,
      children: (
        <div style={{ height: 600 }}>
          <Editor
            height="100%"
            language="python"
            value={newCode}
            options={{
              readOnly: true,
              minimap: { enabled: true },
              scrollBeyondLastLine: false,
              wordWrap: 'on',
            }}
            theme="vs-dark"
          />
        </div>
      ),
    },
  ];

  return (
    <Modal
      title={
        <Space>
          <span>代码对比</span>
          {hasChanges && (
            <span style={{ fontSize: 12, fontWeight: 'normal', color: '#666' }}>
              (+{addedCount} / -{removedCount} / ~{modifiedCount})
            </span>
          )}
        </Space>
      }
      open={visible}
      onCancel={onClose}
      width={1400}
      footer={[
        <Button key="close" onClick={onClose}>
          关闭
        </Button>,
      ]}
      destroyOnClose
    >
      {!hasChanges && (
        <Alert
          message="代码无变化"
          description="两个版本的代码完全相同。"
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}
      
      {hasChanges && (
        <Alert
          message="代码对比说明"
          description={
            <div style={{ fontSize: 12 }}>
              <div>• <span style={{ color: '#52c41a' }}>绿色 (+)</span> 表示新增的行</div>
              <div>• <span style={{ color: '#ff4d4f' }}>红色 (-)</span> 表示删除的行</div>
              <div>• <span style={{ color: '#faad14' }}>黄色 (~)</span> 表示修改的行</div>
              <div>• 并排对比模式可以同时查看两个版本的代码</div>
            </div>
          }
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}
      
      <Tabs items={tabItems} defaultActiveKey="side-by-side" />
    </Modal>
  );
};

export default CodeDiffViewer;
