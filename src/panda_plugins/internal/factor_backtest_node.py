from typing import Optional, Type

from panda_plugins.base import BaseWorkNode, work_node, ui
from pydantic import BaseModel, Field, field_validator
import pandas as pd
from panda_backtest.main_workflow import start


@ui(
    df_factor={"input_type": "None"},
    code={"input_type": "text_field", "placeholder": "策略代码"},
    adjustment_cycle={"input_type": "combobox", "options": ["1", "3", "5", "10", "20", "30"],
                      "placeholder": "请输入调仓周期",
                      "allow_link": False},
    start_date={"input_type": "date_picker", "placeholder": "请输入回测开始时间",
                "allow_link": False},
    end_date={"input_type": "date_picker", "placeholder": "请输入回测结束时间",
              "allow_link": False},
    group_number={"input_type": "combobox",
                  "options": ["2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16",
                              "17", "18", "19", "20"], "placeholder": "请输入因子分组数量", "allow_link": False},
    factor_direction={"input_type": "combobox", "options": ["0", "1"], "placeholder": "请输入因子方向(0:正向，1:负向)",
                      "allow_link": False},
    start_capital={"input_type": "number_field", "placeholder": "请输入初始资金", "allow_link": False},
    standard_symbol={"input_type": "combobox", "options": ["上证指数", "沪深300", "中证500", "中证1000"]},
    commission_rate={"input_type": "number_field", "placeholder": "请输入佣金率", "allow_link": False},
    account_id={"input_type": "text_field", "placeholder": "请输入股票账户（非真实）", "allow_link": False}
)
class FactorBacktestInputModel(BaseModel):
    df_factor: object = Field(title="因子值")
    code:str = Field(default="",title="策略代码")
    start_date: str = Field(default="20241001", title="回测开始时间")
    end_date: str = Field(default="20241231", title="回测结束时间")
    adjustment_cycle: str = Field(default="1", title="调仓周期")
    group_number: str = Field(default="5", title="分组数量")
    factor_direction: str = Field(default="0", title="因子方向(0:负向，1:正向)")
    start_capital: int = Field(default=10000000, title="初始资金")
    standard_symbol: str = Field(default="上证指数", title="基准指数")
    commission_rate: int = Field(default=1, title="佣金率")
    account_id: str = Field(default="8888", title="股票账户")
    model_config = {"arbitrary_types_allowed": True}

    @field_validator('df_factor')
    def validate_df_factor(cls, v):
        if not isinstance(v, pd.DataFrame):
            raise ValueError('df_factor must be a pandas DataFrame')
        return v


class FactorBacktestOutputModel(BaseModel):
    backtest_id: str = Field(default="error", title="回测id")


@work_node(name="股票因子回测", group="05-回测相关", type="general", box_color="yellow")
class FactorBacktestControl(BaseWorkNode):
    # Return the input model
    # 返回输入模型
    @classmethod
    def input_model(cls) -> Optional[Type[BaseModel]]:
        return FactorBacktestInputModel

    # Return the output model
    # 返回输出模型
    @classmethod
    def output_model(cls) -> Optional[Type[BaseModel]]:
        return FactorBacktestOutputModel

    # Node running logic
    # 节点运行逻辑
    def run(self, input: BaseModel) -> BaseModel:
        backtest_id = start(
                            code=input.code,
                            adjustment_cycle=input.adjustment_cycle,
                            start_date=input.start_date,
                            end_date=input.end_date,
                            group_number=input.group_number,
                            factor_direction=input.factor_direction,
                            start_capital=input.start_capital,
                            standard_symbol=input.standard_symbol,
                            commission_rate=input.commission_rate,
                            account_id=input.account_id,
                            df_factor=input.df_factor,
                            )

        return FactorBacktestOutputModel(backtest_id=str(backtest_id))


if __name__ == "__main__":
    node = FactorBacktestControl()
    df = pd.read_csv(
        '/Users/peiqi/code/python/panda_factor/panda_factor/test/1.csv',
        usecols=["date", "symbol", "bs4177e23"],  # 只读取需要的列，节省内存
        dtype={"date": str}  # 明确指定date列为字符串类型
    )
    input = FactorBacktestInputModel(df_factor=df)
    print(node.run(input))
