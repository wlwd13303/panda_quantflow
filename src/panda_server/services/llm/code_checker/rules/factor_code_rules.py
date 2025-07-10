"""
因子代码检查规则
Factor code check rules

参考文档: https://www.pandaai.online/community/article/117
"""

# 允许导入的库: 仅在白名单检查模式下启用, 这个模式下其它导入都视为非法
allowed_imports = [
    "panda_factor",
    "pandas",
    "numpy",
    "scipy",
    "sklearn",
    "datetime",
]

# 不允许导入的库: 仅在黑名单检查模式下启用, 这个模式下其它导入都视为合法
not_allowed_imports = [
    "os",
    "sys",
    "logging",
    "subprocess",
    "shutil",
    "eval",
    "exec",
    "pickle",
    "yaml",
    "marshal",
    "requests",
    "sqlite3",
    "pymysql",
    "pymongo",
    "redis",
    "elasticsearch",
    "kafka",
    "rabbitmq",
]

# 基础因子列表
base_factors = [
    "CLOSE",
    "OPEN",
    "HIGH",
    "LOW",
    "VOLUME",
    "AMOUNT",
    "TURNOVER",
    "MARKET_CAP",
]

# 内置函数列表
builtin_functions = [
    # 基础计算函数
    "RANK",
    "RETURNS",
    "STDDEV",
    "CORRELATION",
    "IF",
    "MIN",
    "MAX",
    "ABS",
    "LOG",
    "POWER",
    "SIGN",
    "SIGNEDPOWER",
    "COVARIANCE",
    
    # 时间序列函数
    "DELAY",
    "SUM",
    "TS_ARGMAX",
    "TS_ARGMIN",
    "TS_MEAN",
    "TS_MIN",
    "TS_MAX",
    "TS_RANK",
    "DECAY_LINEAR",
    "MA",
    "EMA",
    "SMA",
    "DMA",
    "WMA",
    
    # 技术指标函数
    "MACD",
    "KDJ",
    "RSI",
    "BOLL",
    "CCI",
    "ATR",
    "DMI",
    "BBI",
    "TAQ",
    "KTN",
    "TRIX",
    "VR",
    "EMV",
    "DPO",
    "BRAR",
    "MTM",
    "MASS",
    "ROC",
    "EXPMA",
    "OBV",
    "MFI",
    "ASI",
    "PSY",
    "BIAS",
    "WR",
    
    # 价格类函数
    "VWAP",
    "CAP",
    
    # 核心工具函数
    "RD",
    "RET",
    "REF",
    "DIFF",
    "CONST",
    "HHVBARS",
    "LLVBARS",
    "AVEDEV",
    "SLOPE",
    "FORCAST",
    "LAST",
    "COUNT",
    "EVERY",
    "EXIST",
    "FILTER",
    "SUMIF",
    "BARSLAST",
    "BARSLASTCOUNT",
    "BARSSINCEN",
    "CROSS",
    "LONGCROSS",
    "VALUEWHEN",
]

# Python类模式必须实现的方法
mandatory_methods = [
    "calculate",
]

# 关键对象规则
key_object_rules = [
    # factors 对象
    {
        "in_function": ["calculate"],
        "arg_name": "factors",
        "allowed_attributes": base_factors,
        "allowed_methods": [],
        "allow_custom_attributes": False,
        "track_across_functions": True,
    },
]

# 关键内置方法规则
key_method_rules = [
    # 框架方法
    {
        "function_name": "calculate",
        "required_args": ["factors"],
        "optional_args": [],
        "supports_varargs": False,
        "supports_kwargs": False,
    },
]

# 公式模式语法规则
formula_syntax_rules = {
    "allowed_operators": ["+", "-", "*", "/", "(", ")", ",", "=", ">", "<", ">=", "<=", "!="],
    "max_nested_calls": 5,  # 最大嵌套调用深度
    "max_line_length": 500,  # 单行最大长度
} 