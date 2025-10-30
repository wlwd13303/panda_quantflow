import React from 'react';
import { Modal, Tabs, Alert } from 'antd';
import Editor from '@monaco-editor/react';

interface CodeDiffViewerProps {
  visible: boolean;
  oldCode: string;
  newCode: string;
  oldTitle?: string;
  newTitle?: string;
  onClose: () => void;
}

const CodeDiffViewer: React.FC<CodeDiffViewerProps> = ({
  visible,
  oldCode,
  newCode,
  oldTitle = '回测时的代码',
  newTitle = '当前策略代码',
  onClose,
}) => {
  const tabItems = [
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
      title="代码对比"
      open={visible}
      onCancel={onClose}
      width={1200}
      footer={null}
      destroyOnClose
    >
      <Alert
        message="功能说明"
        description="逐行对比功能正在开发中。当前显示两个版本的完整代码，您可以切换Tab查看。"
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
      />
      
      <Tabs items={tabItems} defaultActiveKey="old" />
    </Modal>
  );
};

export default CodeDiffViewer;

