# -*- coding: utf-8 -*-
"""
File: factor_correlation_result_node.py
Author: Bayoro
Date: 2025/7/1
Description: 因子相关性分析结果 - 分析结果热力图
"""
from typing import Optional, Type, Any
import logging

from tornado.process import task_id

from panda_plugins.base import BaseWorkNode, work_node, ui
from pydantic import BaseModel, Field, field_validator
from panda_factor.analysis.factor_analysis_workflow import factor_analysis_workflow
import pandas as pd


@ui(
    task_id={"input_type": "None"},
)
class FactorCorrelationChartInputModel(BaseModel):
    task_id: str = Field(default="error", title="分析结果")

class FactorCorrelationChartOutputModel(BaseModel):
    task_id: str = Field(default="error", title="图表绘制")

@work_node(name="因子相关性检验结果", group="04-因子相关",type="factor_correlation_result", box_color="purple")
class FactorCorrelationChartControl(BaseWorkNode):

    # Return the input model
    # 返回输入模型
    @classmethod
    def input_model(cls) -> Optional[Type[BaseModel]]:
        return FactorCorrelationChartInputModel

    # Return the output model
    # 返回输出模型
    @classmethod
    def output_model(cls) -> Optional[Type[BaseModel]]:
        return FactorCorrelationChartOutputModel

    # Node running logic
    # 节点运行逻辑
    def run(self, input: BaseModel) -> BaseModel:
        print(input.task_id)
        return FactorCorrelationChartControl(task_id=str(input.task_id))

if __name__ == "__main__":
    node = FactorCorrelationChartControl()
    input = FactorCorrelationChartInputModel(task_id="654321")
    node.run(input)