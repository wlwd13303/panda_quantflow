import pandas as pd
import numpy as np
from panda_ml.importance_spearman_factor_combiner import ImportanceSpearmanFactorCombiner

# ── 1. 构造历史重要性数据 importance_history ────────────────────────────────────
# 假设有 4 个交易日，2 个因子（factor1/factor2），3 种指标
dates = pd.to_datetime(['2022-01-01','2022-01-02','2022-01-03','2022-01-04'])
metrics = ['weight','gain','cover']
factors = ['factor1','factor2']
cols = pd.MultiIndex.from_product([metrics, factors])
np.random.seed(42)
importance_history = pd.DataFrame(
    np.random.rand(len(dates), len(metrics)*len(factors)),
    index=dates, columns=cols
)

# ── 2. 构造对应的收益率序列 returns ─────────────────────────────────────────────
# 用来计算 Spearman 相关性的“标签”
returns = pd.Series([0.05, 0.10, -0.02, 0.12], index=dates, name='ret')

# ── 3. 构造当前期的重要性指标 current_importance ────────────────────────────────
current_importance = importance_history.iloc[-1]  # 取最后一天的 weight/gain/cover

# ── 4. 构造横截面因子暴露 x_df ───────────────────────────────────────────────
# 假设我们有两个股票，每个股票对应两个因子的截面暴露
x_df = pd.DataFrame({
    'factor1':[ 0.25,  0.40],
    'factor2':[ 0.10, -0.05]
}, index=['stock_A','stock_B'])

# ── 5. 实例化合成器 & 计算──────────────────────────────────────────────────
combiner = ImportanceSpearmanFactorCombiner()
# （1）fit：计算每个因子三种指标与收益的 Spearman 相关系数
combiner.fit(importance_history, returns)

# （2）compute_weights：给出当前期的综合因子权重 w_j
weights = combiner.compute_weights(current_importance)
print("因子综合权重 w_j：")
print(weights)
# 输出类似：
# factor1    0.58
# factor2   -0.42
# Name: composite_weight, dtype: float64

# （3）transform：拿截面暴露 x_df 乘以权重，得到每只股票的复合因子值 F_i
composite_factor = combiner.transform(x_df, weights)
print("\n每只股票的复合因子值 F_i：")
print(composite_factor)
# 输出类似：
# stock_A    0.58*0.25 + (-0.42)*0.10 = 0.103
# stock_B    0.58*0.40 + (-0.42)*(-0.05) = 0.254

# ── 6. 一步到位：fit_transform ───────────────────────────────────────────────
F = combiner.fit_transform(
    importance_history,  # 历史指标
    returns,             # 收益
    current_importance,  # 当期指标
    x_df                 # 横截面暴露
)
print("\n一步完成的复合因子：")
print(F)
