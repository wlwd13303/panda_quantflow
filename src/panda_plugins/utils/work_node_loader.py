import os
import importlib.util
import sys
import pathlib
from common.logging.system_log import logging, setup_logging

logger = logging.getLogger(__name__)

# 这里定义相对路径部分
INTERNAL_REL = "internal"
CUSTOM_REL = "custom"

def load_all_nodes():
    """
    Load all work nodes from both internal and custom folders.
    
    从内部和自定义文件夹加载所有工作节点。
    """
    current_file = pathlib.Path(__file__).resolve()
    plugins_root = current_file.parent.parent
    
    internal_folder = os.path.join(plugins_root, INTERNAL_REL)
    custom_folder = os.path.join(plugins_root, CUSTOM_REL)
    
    if not os.path.exists(internal_folder):
        os.makedirs(internal_folder, exist_ok=True)
    else:
        load_all_nodes_from_folder(internal_folder)
    if not os.path.exists(custom_folder):
        os.makedirs(custom_folder, exist_ok=True)
    else:
        load_all_nodes_from_folder(custom_folder)
    
    # 防止插件加载时，日志配置被覆盖
    setup_logging()

def load_all_nodes_from_folder(folder_path: str):
    """
    Load all work node modules from the folder and its subfolders.
    
    从文件目录及其所有子目录动态导入所有工作节点模块.
    """
    sys.path.append(folder_path)
    
    loaded_count = 0
    failed_count = 0

    for root, _, files in os.walk(folder_path):
        # Add current subdirectory to sys.path
        # 添加当前子目录到sys.path
        if root != folder_path:
            sys.path.append(root)
            
        for fname in files:
            if fname.endswith(".py") and not fname.startswith("__"):
                fpath = os.path.join(root, fname)
                rel_path = os.path.relpath(fpath, folder_path)
                modulename = os.path.splitext(rel_path)[0].replace(os.path.sep, '.')
                
                if modulename in sys.modules:
                    continue

                spec = importlib.util.spec_from_file_location(modulename, fpath)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    try:
                        spec.loader.exec_module(module)
                        loaded_count += 1
                        logger.debug(f"Loaded {modulename} from {folder_path}/{fname}")
                    except Exception as e:
                        logger.error(f"Failed to load {modulename} from {folder_path}/{fname}: {e}")
                        failed_count += 1
    
    logger.debug(f"From {folder_path}: Loaded {loaded_count} nodes, Failed {failed_count} nodes")
    

if __name__ == "__main__":
    load_all_nodes()