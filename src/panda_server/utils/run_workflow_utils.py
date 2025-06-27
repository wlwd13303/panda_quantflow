import contextlib
import os
import traceback
import logging
import uuid
from typing import Any
from bson import ObjectId
from fastapi.concurrency import run_in_threadpool
from panda_server.enums.workflow_run_status import WorkflowStatus
from panda_server.models.workflow_model import WorkflowModel
from panda_server.config.database import mongodb
from panda_server.models.workflow_run_model import (
    WorkflowRunModel,
    WorkflowRunUpdateModel,
)
from panda_plugins.base.work_node_registery import ALL_WORK_NODES
from panda_server.utils.db_storage import save_to_gridfs

logger = logging.getLogger(__name__)


def generate_friendly_error_message(error, node, node_input_model, input_data):
    """生成友好的错误信息和修复建议"""
    error_type = type(error).__name__
    error_str = str(error)
    node_type = node.type
    node_name = node.name

    suggestions = []

    # 处理 Pydantic 验证错误
    if error_type == "ValidationError" and "Field required" in error_str:
        # 解析缺少的字段
        missing_fields = []
        if "df_factor" in error_str:
            missing_fields.append("df_factor")

        for field in missing_fields:
            suggestions.extend(
                [
                    f"❌ 节点 '{node_name}' ({node_type}) 缺少必需的输入字段: '{field}'",
                    f"",
                    f"🔧 修复建议:",
                    f"1. 检查工作流图中是否有节点连接到该节点的 '{field}' 输入端口",
                    f"2. 常见的 {field} 数据源节点:",
                ]
            )

            if field == "df_factor":
                suggestions.extend(
                    [
                        f"   - 公式节点 (formula_node): 输出字段 'df' 或 'result'",
                        f"   - 因子构建节点 (factor_build_node): 输出字段 'factor'",
                        f"   - 斯皮尔曼因子构建节点 (spearman_factor_build_node): 输出字段 'factor'",
                        f"   - PCA因子构建节点 (pca_factor_build_node): 输出字段 'factor'",
                    ]
                )
            elif field == "train_data":
                suggestions.extend(
                    [
                        f"   - CSV读取节点 (read_csv_node): 输出字段 'df'",
                        f"   - 特征工程节点 (feature_engineering_node): 输出字段 'processed_data'",
                        f"   - 因子构建节点 (factor_build_node): 输出字段 'factor'",
                    ]
                )

            suggestions.extend(
                [
                    f"",
                    f"3. 连接配置步骤:",
                    f"   - 找到输出 {field} 相关数据的节点",
                    f"   - 将该节点的输出端口连接到当前节点的 '{field}' 输入端口",
                    f"   - 确保字段映射正确",
                    f"",
                    f"4. 当前接收到的输入字段: {list(input_data.keys())}",
                    f"   缺少的必需字段: {field}",
                ]
            )

    # 处理其他常见错误
    elif "DataFrame" in error_str:
        suggestions.extend(
            [
                f"❌ 数据格式错误: 期望 pandas DataFrame，但接收到其他类型",
                f"",
                f"🔧 修复建议:",
                f"1. 检查前置节点是否正确输出 DataFrame 格式的数据",
                f"2. 验证连接的字段是否包含有效的 DataFrame",
                f"3. 检查前置节点的执行日志，确认数据生成正常",
            ]
        )

    elif "import" in error_str.lower() or "module" in error_str.lower():
        suggestions.extend(
            [
                f"❌ 模块导入错误",
                f"",
                f"🔧 修复建议:",
                f"1. 检查相关依赖包是否已安装",
                f"2. 验证 Python 路径配置",
                f"3. 重启服务以重新加载模块",
            ]
        )

    else:
        suggestions.extend(
            [
                f"❌ 节点执行错误: {error_str}",
                f"",
                f"🔧 通用修复建议:",
                f"1. 检查节点配置参数是否正确",
                f"2. 验证输入数据格式和内容",
                f"3. 查看节点执行日志获取更多信息",
                f"4. 尝试单独测试该节点功能",
            ]
        )

    # 添加调试信息
    suggestions.extend(
        [
            f"",
            f"📊 调试信息:",
            f"- 节点类型: {node_type}",
            f"- 节点名称: {node_name}",
            f"- 错误类型: {error_type}",
            f"- 接收到的输入字段: {list(input_data.keys())}",
        ]
    )

    # 尝试获取模型字段信息
    try:
        if hasattr(node_input_model, "model_fields"):
            required_fields = []
            optional_fields = []

            for field_name, field_info in node_input_model.model_fields.items():
                if field_info.is_required():
                    required_fields.append(field_name)
                else:
                    default_value = getattr(field_info, "default", None)
                    optional_fields.append(f"{field_name} (默认: {default_value})")

            suggestions.extend(
                [
                    f"- 必需字段: {required_fields}",
                    f"- 可选字段: {optional_fields}",
                ]
            )
    except:
        pass

    return "\n".join(suggestions)


async def run_workflow_in_background(workflow_run_id):
    # 生成唯一执行ID
    execution_id = str(uuid.uuid4())[:8]

    logger.info(
        f"🚀 [EXEC:{execution_id}] run_workflow_logic: start, workflow_run_id: {workflow_run_id}"
    )

    # 从 mongodb 中获取 workflow run 信息
    workflow_run_collection = mongodb.get_collection("workflow_run")
    query_result = await workflow_run_collection.find_one(
        {"_id": ObjectId(workflow_run_id)}
    )
    if not query_result:
        logger.error(f"No workflow run found, id: {workflow_run_id}")
        return

    workflow_run = WorkflowRunModel(**query_result)

    workflow_id = workflow_run.workflow_id

    # 创建工作流级别的用户日志记录器
    try:
        from common.logging.workflow_log import WorkflowLogger
        workflow_logger = WorkflowLogger(
            user_id=workflow_run.owner,
            workflow_run_id=workflow_run_id,
            work_node_id=None,  # None表示工作流级别
        )
        await workflow_logger.info("工作流开始执行", workflow_id=workflow_id)
    except Exception as e:
        logger.error(f"Failed to create workflow logger, terminating workflow: {e}")
        return

    # 从 mongodb 中获取 workflow 信息
    workflow_collection = mongodb.get_collection("workflow")
    query_result = await workflow_collection.find_one({"_id": ObjectId(workflow_id)})
    if not query_result:
        logger.error(f"No workflow found, id: {workflow_id}")
        if workflow_logger:
            await workflow_logger.error("未找到工作流定义", workflow_id=workflow_id)
        return

    workflow = WorkflowModel(**query_result)

    # 得到分层排序好的节点列表
    try:
        execution_layers = determine_workflow_execution_order(workflow)
        await workflow_logger.info(
            "工作流执行顺序确定完成",
            workflow_id=workflow_id,
            layers_count=len(execution_layers),
            total_nodes=sum(len(layer) for layer in execution_layers),
        )
    except Exception as e:
        logger.error(
            f"Error determining workflow execution order, id: {workflow_run_id}, error: {e}"
        )
        await workflow_logger.error(
            "工作流执行顺序确定失败", workflow_id=workflow_id, error=str(e)
        )
        await mark_workflow_run_failed(workflow_run_id, str(e), traceback.format_exc())
        workflow_run_update_data = WorkflowRunUpdateModel(status=WorkflowStatus.FAILED)
        workflow_run_collection = mongodb.get_collection("workflow_run")
        await workflow_run_collection.update_one(
            {"_id": ObjectId(workflow_run_id)},
            {"$set": workflow_run_update_data.model_dump(exclude_unset=True)},
        )
        return

    logger.info(
        f"🔄 [EXEC:{execution_id}] run_workflow_logic: execution_order determined: {execution_layers}"
    )

    # 简化版的执行逻辑 (单线程执行)
    node_outputs: dict[str, Any] = {}
    failed_node_ids = []
    success_node_ids = []
    passed_link_ids = []
    for layer_index, layer in enumerate(execution_layers):
        if await is_workflow_run_terminated(workflow_run_id):
            logger.info(f"Workflow run terminated, id: {workflow_run_id}")
            await workflow_logger.warning("工作流执行被手动终止", workflow_id=workflow_id)
            return
        logger.info(
            f"⚡ [EXEC:{execution_id}] run_workflow_logic: running layer: {layer}"
        )
        await workflow_logger.info(
            f"开始执行第 {layer_index + 1} 层节点",
            workflow_id=workflow_id,
            layer_index=layer_index + 1,
            nodes_in_layer=len(layer),
        )
        progress = layer_index / len(execution_layers) * 100
        workflow_run_update_data = WorkflowRunUpdateModel(
            status=WorkflowStatus.RUNNING,
            progress=progress,
            running_node_ids=layer,
            failed_node_ids=failed_node_ids,
            success_node_ids=success_node_ids,
            passed_link_ids=passed_link_ids,
        )
        workflow_run_collection = mongodb.get_collection("workflow_run")
        await workflow_run_collection.update_one(
            {"_id": ObjectId(workflow_run_id)},
            {"$set": workflow_run_update_data.model_dump(exclude_unset=True)},
        )
        logger.debug(
            f"run_workflow_logic: workflow_run_update_data: {workflow_run_update_data}"
        )

        # 并行执行当前层的所有节点
        for node_id in layer:
            if await is_workflow_run_terminated(workflow_run_id):
                logger.info(f"Workflow run terminated, id: {workflow_run_id}")
                await workflow_logger.warning(
                    "工作流执行被手动终止", workflow_id=workflow_id, work_node_id=node_id
                )
                return
            try:
                # 获取节点信息
                node = [n for n in workflow.nodes if n.uuid == node_id][0]
                logger.info(
                    f"🔧 [EXEC:{execution_id}] run_workflow_logic: running work node id: {node_id}, name: {node.name}"
                )
                node_class = ALL_WORK_NODES.get(node.name)
                node_instance = node_class()
                # 设置节点的日志上下文，使用户在节点中调用 self.log_info 等方法时能存储到数据库
                node_instance._setup_logging_context(
                    user_id=workflow_run.owner,
                    workflow_run_id=workflow_run_id,
                    work_node_id=node_id,
                    workflow_id=workflow_id
                )
                node_input_model = node_class.input_model()
                # 注入静态的输入字段
                input_data = node.static_input_data.copy()
                logger.debug(
                    f"📊 [EXEC:{execution_id}] run_workflow_logic: got static input data: {input_data}"
                )
                # 注入动态的从前置节点获得的输入字段
                previous_links = [
                    link for link in workflow.links if link.next_node_uuid == node.uuid
                ]
                for link in previous_links:
                    previous_node_uuid = link.previous_node_uuid
                    target_input_data = (
                        node_outputs[previous_node_uuid]
                        .model_dump()
                        .get(link.input_field_name)
                    )
                    logger.debug(
                        f"🔗 [EXEC:{execution_id}] run_workflow_logic: got data from link: link_input_field_name: {link.input_field_name}, link_output_field_name: {link.output_field_name}, data: {target_input_data}"
                    )
                    input_data[link.output_field_name] = target_input_data
                logger.info(
                    f"▶️ [EXEC:{execution_id}] run_workflow_logic: running work node id: {node_id}, name: {node.name}, got input_data: {input_data}"
                )
                node_input = node_input_model(**input_data)
                await workflow_logger.debug(
                    "节点输入数据", workflow_id=workflow_id, work_node_id=node_id, input_fields=list(input_data.keys())
                )
                node_output = await run_in_threadpool(
                    lambda: run_without_stdout(node_instance.run, node_input)
                )
                # 处理节点执行期间产生的队列日志
                await node_instance._process_queued_logs()
                await workflow_logger.info(
                    f"节点 {node.name} 执行成功", workflow_id=workflow_id, work_node_id=node_id, has_output=node_output is not None
                )
                node_outputs[node_id] = node_output
                # 保存节点输出到数据库
                output_db_id = await save_output_to_db(
                    workflow_run_id, node_id, workflow_run.owner, node_output
                )
                node.output_db_id = output_db_id
                # 更新成功节点
                success_node_ids.append(node_id)
                # 更新通过的连接
                passed_link_ids.extend(link.uuid for link in previous_links)
            except Exception as e:
                failed_node_ids.append(node_id)
                stack_trace = traceback.format_exc()

                # 处理节点执行期间产生的队列日志（即使节点失败）
                try:
                    await node_instance._process_queued_logs()
                except Exception as log_error:
                    logger.warning(f"Failed to process queued logs for failed node {node_id}: {log_error}")

                # 生成友好的错误信息
                friendly_error = generate_friendly_error_message(
                    e, node, node_input_model, input_data
                )
                logger.error(
                    f"Error running workflow, id: {workflow_run_id}, failed node: {node_id} error: {e},\nstack_trace: {stack_trace}\n\n=== 错误分析与修复建议 ===\n{friendly_error}"
                )
                await mark_workflow_run_failed(
                    workflow_run_id, str(e), stack_trace, failed_node_ids
                )
                await workflow_logger.error(
                    "节点执行失败",
                    workflow_id=workflow_id,
                    work_node_id=node_id,
                    node_name=node.name,
                    error=str(e),
                    suggestions=friendly_error,
                )
                workflow_run_update_data = WorkflowRunUpdateModel(
                    status=WorkflowStatus.FAILED,
                    failed_node_ids=failed_node_ids,
                    last_error_message=str(e),
                    last_error_stacktrace=stack_trace,
                )
                workflow_run_collection = mongodb.get_collection("workflow_run")
                await workflow_run_collection.update_one(
                    {"_id": ObjectId(workflow_run_id)},
                    {"$set": workflow_run_update_data.model_dump(exclude_unset=True)},
                )
                return

    logger.info(
        f"run_workflow_logic: all nodes executed successfully, workflow_run_id: {workflow_run_id}"
    )
    await workflow_logger.info(
        "工作流执行完成", workflow_id=workflow_id, total_nodes=len(success_node_ids)
    )
    workflow_run_update_data = WorkflowRunUpdateModel(
        status=WorkflowStatus.SUCCESS,
        progress=100,
        running_node_ids=[],
        failed_node_ids=[],
        success_node_ids=[node.uuid for node in workflow.nodes],
        passed_link_ids=[link.uuid for link in workflow.links],
        output_data_obj={node.uuid: node.output_db_id for node in workflow.nodes},
    )
    workflow_run_collection = mongodb.get_collection("workflow_run")
    await workflow_run_collection.update_one(
        {"_id": ObjectId(workflow_run_id)},
        {"$set": workflow_run_update_data.model_dump(exclude_unset=True)},
    )


async def is_workflow_run_terminated(workflow_run_id):
    workflow_run_collection = mongodb.get_collection("workflow_run")
    workflow_run_query_result = await workflow_run_collection.find_one(
        {"_id": ObjectId(workflow_run_id)}
    )
    if workflow_run_query_result.get("status") == WorkflowStatus.MANUAL_STOP:
        return True
    return False


async def save_output_to_db(workflow_run_id, node_id, owner, node_output) -> str:
    extra = {
        "workflow_run_id": workflow_run_id,
        "node_id": node_id,
        "owner": owner,
    }
    return await save_to_gridfs("workflow_node_output_fs", node_output, extra=extra)


def determine_workflow_execution_order(workflow_model):
    """
    确定工作流节点的执行顺序

    参数:
        workflow_model: WorkflowModel 对象

    返回:
        执行序列列表，每个元素是可以并行执行的节点列表
        二维列表例如: [[node_id1, node_id2], [node_id3], [node_id4, node_id5]]
    """
    # 1. 构建节点依赖关系图
    node_dependencies = {}  # 记录每个节点依赖的前置节点数量
    node_successors = {}  # 记录每个节点的后续节点

    # 初始化依赖关系
    for node in workflow_model.nodes:
        node_dependencies[node.uuid] = 0
        node_successors[node.uuid] = []

    # 填充依赖关系
    for link in workflow_model.links:
        from_node = link.previous_node_uuid
        to_node = link.next_node_uuid

        # 增加目标节点的依赖计数
        node_dependencies[to_node] += 1

        # 添加源节点的后继节点
        node_successors[from_node].append(to_node)

    # 2. 找出所有入度为0的节点（没有依赖的节点）作为起始点
    start_nodes = [
        node_id
        for node_id, dependencies in node_dependencies.items()
        if dependencies == 0
    ]

    if not start_nodes:
        # 如果没有起始节点，可能存在循环依赖
        raise ValueError("工作流中存在循环依赖，无法确定执行顺序")

    # 3. 执行拓扑排序，按层次组织节点
    execution_layers = []
    remaining_nodes = set(node_dependencies.keys())

    while start_nodes:
        # 当前层可以并行执行的节点
        current_layer = start_nodes
        execution_layers.append(current_layer)

        # 移除已处理的节点
        remaining_nodes -= set(current_layer)

        # 查找下一层节点
        next_layer = []
        for node_id in current_layer:
            # 处理当前节点的所有后继节点
            for successor in node_successors[node_id]:
                # 减少依赖计数
                node_dependencies[successor] -= 1

                # 如果所有依赖都已满足，加入下一层
                if node_dependencies[successor] == 0:
                    next_layer.append(successor)

        # 更新起始节点为下一层节点
        start_nodes = next_layer

    # 检查是否所有节点都已处理
    if remaining_nodes:
        # 如果还有未处理的节点，说明存在环形依赖
        raise ValueError(f"工作流中存在无法到达的节点或循环依赖: {remaining_nodes}")

    return execution_layers


async def mark_workflow_run_failed(
    workflow_run_id, error_message, error_stacktrace, failed_node_ids=[]
):
    """
    标记工作流运行失败
    """
    workflow_run_update_data = WorkflowRunUpdateModel(
        status=WorkflowStatus.FAILED,
        last_error_message=error_message,
        last_error_stacktrace=error_stacktrace,
        failed_node_ids=failed_node_ids,
    )
    workflow_run_collection = mongodb.get_collection("workflow_run")
    await workflow_run_collection.update_one(
        {"_id": ObjectId(workflow_run_id)},
        {"$set": workflow_run_update_data.model_dump(exclude_unset=True)},
    )


# 禁用控制台输出运行某段逻辑
def run_without_stdout(func, *args, **kwargs):
    # with open(os.devnull, "w") as devnull:
    #     with contextlib.redirect_stdout(devnull), contextlib.redirect_stderr(devnull):
    return func(*args, **kwargs)


# TODO 待完善, 完整的多线程工作流执行+每一步存储状态的方法
def execute_workflow(workflow_model, workflow_run_id):
    """
    执行工作流，按照确定的顺序依次执行节点

    参数:
        workflow_model: WorkflowModel 对象
        workflow_run_id: 工作流运行ID
    """
    # 确定执行顺序
    execution_layers = determine_workflow_execution_order(workflow_model)

    # 跟踪完成的节点和其输出
    completed_nodes = {}

    # 更新工作流运行状态为运行中
    update_workflow_run_status(workflow_run_id, WorkflowStatus.RUNNING)

    # 按层次执行节点
    for layer_index, layer in enumerate(execution_layers):
        # 当前层节点进度占比
        layer_progress = 100.0 / len(execution_layers)

        # 更新运行中的节点
        update_running_nodes(workflow_run_id, layer)

        # 并行执行当前层的所有节点
        layer_results = {}

        for node_id in layer:
            try:
                # 获取节点信息
                node = get_node_by_id(workflow_model, node_id)

                # 收集节点输入数据（从前置节点和静态输入）
                inputs = collect_node_inputs(
                    node, completed_nodes, workflow_model.links
                )

                # 执行节点
                result = execute_node(node, inputs)

                # 记录成功节点和结果
                layer_results[node_id] = result
                add_success_node(workflow_run_id, node_id)

                # 存储节点输出到数据库
                output_db_id = store_node_output(result)
                update_node_output_id(workflow_run_id, node_id, output_db_id)

            except Exception as e:
                # 记录失败节点
                add_failed_node(workflow_run_id, node_id)
                log_node_error(workflow_run_id, node_id, str(e))

        # 更新已完成节点
        completed_nodes.update(layer_results)

        # 更新工作流进度
        current_progress = (layer_index + 1) * layer_progress
        update_workflow_progress(workflow_run_id, current_progress)

        # 更新已通过的连接
        update_passed_links(workflow_run_id, layer, workflow_model.links)

    # 检查是否所有节点都成功完成
    all_nodes = set(node.uuid for node in workflow_model.nodes)
    failed_nodes = get_failed_nodes(workflow_run_id)

    if failed_nodes:
        # 存在失败节点，工作流失败
        update_workflow_run_status(workflow_run_id, WorkflowStatus.FAILED)
    else:
        # 所有节点都成功完成，工作流成功
        update_workflow_run_status(workflow_run_id, WorkflowStatus.SUCCESS)
