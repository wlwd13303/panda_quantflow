import React, { useMemo, useRef, useEffect } from 'react';
import { Modal, Tabs, Alert, Space, Button, Statistic, Row, Col } from 'antd';
import Editor, { DiffEditor } from '@monaco-editor/react';
import type { editor } from 'monaco-editor';

interface CodeDiffViewerProps {
  visible: boolean;
  oldCode: string;
  newCode: string;
  oldTitle?: string;
  newTitle?: string;
  onClose: () => void;
}

// 简单的逐行对比函数（用于统计）
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
  oldTitle = '已保存的代码',
  newTitle = '当前代码',
  onClose,
}) => {
  const diffEditorRef = useRef<editor.IStandaloneDiffEditor | null>(null);
  const oldEditorRef = useRef<editor.IStandaloneCodeEditor | null>(null);
  const newEditorRef = useRef<editor.IStandaloneCodeEditor | null>(null);

  // 清理编辑器实例（组件卸载时的最后保障）
  useEffect(() => {
    return () => {
      // 组件卸载时清理编辑器
      if (diffEditorRef.current) {
        try {
          const diffEditor = diffEditorRef.current;
          // 先重置模型，避免 TextModel 被提前销毁
          const originalModel = diffEditor.getOriginalEditor().getModel();
          const modifiedModel = diffEditor.getModifiedEditor().getModel();
          
          // 重置模型为 null，然后再销毁编辑器
          if (originalModel && !originalModel.isDisposed()) {
            diffEditor.getOriginalEditor().setModel(null);
          }
          if (modifiedModel && !modifiedModel.isDisposed()) {
            diffEditor.getModifiedEditor().setModel(null);
          }
          
          diffEditor.dispose();
        } catch (error) {
          // 忽略清理时的错误
          console.warn('Error disposing diff editor:', error);
        }
        diffEditorRef.current = null;
      }
      
      if (oldEditorRef.current) {
        try {
          const editor = oldEditorRef.current;
          const model = editor.getModel();
          if (model && !model.isDisposed()) {
            editor.setModel(null);
          }
          editor.dispose();
        } catch (error) {
          console.warn('Error disposing old editor:', error);
        }
        oldEditorRef.current = null;
      }
      
      if (newEditorRef.current) {
        try {
          const editor = newEditorRef.current;
          const model = editor.getModel();
          if (model && !model.isDisposed()) {
            editor.setModel(null);
          }
          editor.dispose();
        } catch (error) {
          console.warn('Error disposing new editor:', error);
        }
        newEditorRef.current = null;
      }
    };
  }, []);

  const diff = useMemo(() => diffLines(oldCode, newCode), [oldCode, newCode]);
  
  const addedCount = diff.filter(d => d.type === 'added').length;
  const removedCount = diff.filter(d => d.type === 'removed').length;
  const modifiedCount = diff.filter(d => d.type === 'modified').length;
  const hasChanges = addedCount > 0 || removedCount > 0 || modifiedCount > 0;

  // 处理关闭，先清理编辑器模型
  const handleClose = () => {
    // 先重置 DiffEditor 的模型
    if (diffEditorRef.current) {
      try {
        const diffEditor = diffEditorRef.current;
        const originalModel = diffEditor.getOriginalEditor().getModel();
        const modifiedModel = diffEditor.getModifiedEditor().getModel();
        
        if (originalModel && !originalModel.isDisposed()) {
          diffEditor.getOriginalEditor().setModel(null);
        }
        if (modifiedModel && !modifiedModel.isDisposed()) {
          diffEditor.getModifiedEditor().setModel(null);
        }
      } catch (error) {
        // 忽略错误，继续关闭
        console.warn('Error resetting diff editor models:', error);
      }
    }
    
    // 重置其他编辑器的模型
    if (oldEditorRef.current) {
      try {
        const editor = oldEditorRef.current;
        const model = editor.getModel();
        if (model && !model.isDisposed()) {
          editor.setModel(null);
        }
      } catch (error) {
        console.warn('Error resetting old editor model:', error);
      }
    }
    
    if (newEditorRef.current) {
      try {
        const editor = newEditorRef.current;
        const model = editor.getModel();
        if (model && !model.isDisposed()) {
          editor.setModel(null);
        }
      } catch (error) {
        console.warn('Error resetting new editor model:', error);
      }
    }
    
    // 调用原始的 onClose
    onClose();
  };

  const tabItems = [
    {
      key: 'side-by-side',
      label: '并排对比',
      children: (
        <div style={{ height: 600, border: '1px solid #d9d9d9', borderRadius: 4, overflow: 'hidden' }}>
          <DiffEditor
            height="100%"
            language="python"
            original={oldCode}
            modified={newCode}
            onMount={(editor) => {
              diffEditorRef.current = editor;
            }}
            options={{
              readOnly: true,
              minimap: { enabled: true },
              scrollBeyondLastLine: false,
              wordWrap: 'on',
              lineNumbers: 'on',
              renderSideBySide: true,
              enableSplitViewResizing: true,
              renderIndicators: true,
              ignoreTrimWhitespace: false,
              renderOverviewRuler: true,
              overviewRulerLanes: 2,
              overviewRulerBorder: true,
              scrollbar: {
                vertical: 'auto',
                horizontal: 'auto',
                useShadows: true,
                verticalHasArrows: false,
                horizontalHasArrows: false,
              },
              diffWordWrap: 'on',
              originalEditable: false,
              fontSize: 13,
              fontFamily: 'Consolas, "Courier New", monospace',
              lineHeight: 20,
              padding: { top: 10, bottom: 10 },
              // 自定义差异颜色
              diffCodeLens: true,
            }}
            theme="vs-dark"
            loading={
              <div style={{ 
                display: 'flex', 
                alignItems: 'center', 
                justifyContent: 'center', 
                height: '100%',
                color: '#999'
              }}>
                加载中...
              </div>
            }
          />
        </div>
      ),
    },
    {
      key: 'old',
      label: oldTitle,
      children: (
        <div style={{ height: 600, border: '1px solid #d9d9d9', borderRadius: 4, overflow: 'hidden' }}>
          <Editor
            height="100%"
            language="python"
            value={oldCode}
            onMount={(editor) => {
              oldEditorRef.current = editor;
            }}
            options={{
              readOnly: true,
              minimap: { enabled: true },
              scrollBeyondLastLine: false,
              wordWrap: 'on',
              lineNumbers: 'on',
              fontSize: 13,
              fontFamily: 'Consolas, "Courier New", monospace',
              lineHeight: 20,
              padding: { top: 10, bottom: 10 },
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
        <div style={{ height: 600, border: '1px solid #d9d9d9', borderRadius: 4, overflow: 'hidden' }}>
          <Editor
            height="100%"
            language="python"
            value={newCode}
            onMount={(editor) => {
              newEditorRef.current = editor;
            }}
            options={{
              readOnly: true,
              minimap: { enabled: true },
              scrollBeyondLastLine: false,
              wordWrap: 'on',
              lineNumbers: 'on',
              fontSize: 13,
              fontFamily: 'Consolas, "Courier New", monospace',
              lineHeight: 20,
              padding: { top: 10, bottom: 10 },
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
      onCancel={handleClose}
      width={1600}
      style={{ top: 20 }}
      footer={[
        <Button key="close" type="primary" onClick={handleClose}>
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
        <>
          <Row gutter={16} style={{ marginBottom: 16 }}>
            <Col span={8}>
              <Statistic
                title="新增行数"
                value={addedCount}
                valueStyle={{ color: '#52c41a' }}
                prefix="+"
              />
            </Col>
            <Col span={8}>
              <Statistic
                title="删除行数"
                value={removedCount}
                valueStyle={{ color: '#ff4d4f' }}
                prefix="-"
              />
            </Col>
            <Col span={8}>
              <Statistic
                title="修改行数"
                value={modifiedCount}
                valueStyle={{ color: '#faad14' }}
                prefix="~"
              />
            </Col>
          </Row>
          <Alert
            message="使用提示"
            description={
              <div style={{ fontSize: 12 }}>
                <div>• <strong>并排对比模式</strong>：使用 Monaco Editor 的专业 diff 视图，支持同步滚动、差异高亮和智能对齐</div>
                <div>• <span style={{ color: '#52c41a' }}>绿色背景</span> 表示新增的行，<span style={{ color: '#ff4d4f' }}>红色背景</span> 表示删除的行</div>
                <div>• 可以拖动中间的分隔线调整左右面板的宽度比例</div>
                <div>• 使用右侧的概览标尺快速定位差异位置</div>
              </div>
            }
            type="info"
            showIcon
            style={{ marginBottom: 16 }}
          />
        </>
      )}
      
      <Tabs items={tabItems} defaultActiveKey="side-by-side" />
    </Modal>
  );
};

export default CodeDiffViewer;
