import os

import platform
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
def set_chinese_font():
    """通用中文显示配置函数"""
    plt.rcParams['font.sans-serif'] = ['SimHei']  # 设置默认字体
    plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

    # 针对不同系统的额外配置
    system = platform.system()
    if system == 'Darwin':  # MacOS
        plt.rcParams['font.sans-serif'] = ['Arial Unicode MS']
    elif system == 'Linux':
        plt.rcParams['font.sans-serif'] = ['WenQuanYi Zen Hei']
# 使用示例
set_chinese_font()

from typing import Dict, Iterable, Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import tushare as ts


TUSHARE_TOKEN = os.getenv("TUSHARE_TOKEN", "bb30a9f53019f70a1bbf2edb5d67587974a0cc5cde8f11f680672261")
pro = ts.pro_api(TUSHARE_TOKEN)

参数配置表 = {
    # 谨慎庄家: 低换手、慢拉升、持有更久
    "conservative": {
        "年化资金成本": 0.06,
        "最小换手率": 0.0005,
        "最大换手率": 0.15,
        "阈值窗口": 240,
        "阈值最少样本": 120,
        "低分位": 0.10,
        "高分位": 0.90,
        "低位默认值": -15.0,
        "高位默认值": 30.0,
        "回看天数": 120,
        "拉升斜率阈值": 0.12,
        "放弃偏离均值阈值": -25.0,
        "放弃换手率阈值": 0.008,
        "收敛加速回看天数": 8,
        "底背离回看天数": 30,
        "水下蓄力天数": 8,
        "水下蓄力偏离上限": -2.0,
        "水下蓄力偏离下限": -10.0,
        "成本收敛当前阈值": 4.0,
        "成本收敛前期阈值": 10.0,
        "缩量吸筹量比": 1.15,
        "缩量吸筹振幅比": 0.85,
        "振幅异常倍数": 1.6,
        "反弹过度百分比": 18.0,
        "突破强度阈值": 55,
    },
    # 中性: 默认建议
    "neutral": {
        "年化资金成本": 0.01,
        "最小换手率": 0.0010,
        "最大换手率": 0.35,
        "阈值窗口": 120,
        "阈值最少样本": 60,
        "低分位": 0.20,
        "高分位": 0.80,
        "低位默认值": -12.0,
        "高位默认值": 25.0,
        "回看天数": 60,
        "拉升斜率阈值": 0.25,
        "放弃偏离均值阈值": -18.0,
        "放弃换手率阈值": 0.015,
        "收敛加速回看天数": 5,
        "底背离回看天数": 20,
        "水下蓄力天数": 5,
        "水下蓄力偏离上限": -3.0,
        "水下蓄力偏离下限": -8.0,
        "成本收敛当前阈值": 3.0,
        "成本收敛前期阈值": 8.0,
        "缩量吸筹量比": 1.2,
        "缩量吸筹振幅比": 0.9,
        "振幅异常倍数": 1.5,
        "反弹过度百分比": 15.0,
        "突破强度阈值": 50,
    },
    # 激进: 高换手、快节奏
    "aggressive": {
        "年化资金成本": 0.14,
        "最小换手率": 0.0020,
        "最大换手率": 0.45,
        "阈值窗口": 90,
        "阈值最少样本": 45,
        "低分位": 0.25,
        "高分位": 0.75,
        "低位默认值": -10.0,
        "高位默认值": 20.0,
        "回看天数": 45,
        "拉升斜率阈值": 0.35,
        "放弃偏离均值阈值": -15.0,
        "放弃换手率阈值": 0.020,
        "收敛加速回看天数": 4,
        "底背离回看天数": 15,
        "水下蓄力天数": 4,
        "水下蓄力偏离上限": -2.0,
        "水下蓄力偏离下限": -6.0,
        "成本收敛当前阈值": 2.5,
        "成本收敛前期阈值": 6.0,
        "缩量吸筹量比": 1.25,
        "缩量吸筹振幅比": 0.92,
        "振幅异常倍数": 1.4,
        "反弹过度百分比": 12.0,
        "突破强度阈值": 45,
    },
}


def 获取参数配置(参数档位: str) -> Dict[str, float]:
    档位 = (参数档位 or "neutral").lower()
    if 档位 not in 参数配置表:
        可选档位 = ", ".join(参数配置表.keys())
        raise ValueError(f"未知参数档位={参数档位}，可选: {可选档位}")
    return dict(参数配置表[档位])


def get_stock_data(股票代码: str, 开始日期: str, 结束日期: str) -> pd.DataFrame:
    """获取日线与换手率数据。"""
    price_df = pro.daily(ts_code=股票代码, start_date=开始日期, end_date=结束日期)
    if price_df.empty:
        return price_df

    try:
        basic_df = pro.daily_basic(
            ts_code=股票代码,
            start_date=开始日期,
            end_date=结束日期,
            fields="ts_code,trade_date,turnover_rate,turnover_rate_f",
        )
    except Exception:
        basic_df = pd.DataFrame(columns=["trade_date", "turnover_rate", "turnover_rate_f"])

    df = price_df.merge(
        basic_df[["trade_date", "turnover_rate", "turnover_rate_f"]],
        on="trade_date",
        how="left",
    )
    df = df.sort_values("trade_date")
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    df.set_index("trade_date", inplace=True)

    df["typical_price"] = (df["high"] + df["low"] + df["close"]) / 3
    df["turnover_rate_used"] = df["turnover_rate_f"].fillna(df["turnover_rate"])

    vol_ma60 = df["vol"].rolling(60, min_periods=20).mean()
    proxy_turnover = ((df["vol"] / vol_ma60).replace([np.inf, -np.inf], np.nan).fillna(1.0) * 2.0).clip(0.3, 20.0)

    if df["turnover_rate_used"].notna().sum() == 0:
        df["turnover_rate_used"] = proxy_turnover
        df["turnover_source"] = "proxy"
    else:
        rolling_med = df["turnover_rate_used"].rolling(20, min_periods=1).median()
        df["turnover_rate_used"] = df["turnover_rate_used"].fillna(rolling_med).fillna(proxy_turnover)
        df["turnover_source"] = np.where(df["turnover_rate_f"].fillna(df["turnover_rate"]).notna(), "official", "filled")

    return df


def calc_vwap(df: pd.DataFrame, 起始索引: Optional[int] = None) -> pd.DataFrame:
    """计算累计VWAP。"""
    if 起始索引 is None:
        df["vwap"] = (df["typical_price"] * df["vol"]).cumsum() / df["vol"].cumsum()
    else:
        df_sub = df.iloc[起始索引:]
        vwap_sub = (df_sub["typical_price"] * df_sub["vol"]).cumsum() / df_sub["vol"].cumsum()
        df["vwap"] = np.nan
        df.iloc[起始索引:, df.columns.get_loc("vwap")] = vwap_sub
    return df


def calc_dynamic_cost(
    df: pd.DataFrame,
    年化资金成本: float = 0.10,
    建仓起始日期: Optional[str] = None,
    年交易日: int = 252,
    最小换手率: float = 0.001,
    最大换手率: float = 0.35,
) -> pd.DataFrame:
    """
    用换手率递推成本:
    C_t = (1 - τ_t) * C_(t-1) * (1 + r_d) + τ_t * P_t
    """
    if df.empty:
        return df

    if 建仓起始日期 is None:
        start_ts = df.index[0]
    else:
        start_ts = pd.Timestamp(建仓起始日期)

    start_idx = int(df.index.searchsorted(start_ts, side="left"))
    if start_idx >= len(df):
        raise ValueError(f"建仓起始日期={建仓起始日期} 晚于数据末尾，无法计算成本线")

    daily_rate = (1 + 年化资金成本) ** (1 / 年交易日) - 1
    tau = (df["turnover_rate_used"] / 100.0).clip(最小换手率, 最大换手率).to_numpy()

    tp = df["typical_price"].to_numpy()
    vwap = df["vwap"].to_numpy()
    dynamic_cost = np.full(len(df), np.nan, dtype=float)

    dynamic_cost[start_idx] = vwap[start_idx]
    for i in range(start_idx + 1, len(df)):
        carried = dynamic_cost[i - 1] * (1 + daily_rate)
        dynamic_cost[i] = (1 - tau[i]) * carried + tau[i] * tp[i]

    df["effective_turnover"] = tau
    df["days_held"] = np.where(np.arange(len(df)) >= start_idx, np.arange(len(df)) - start_idx, np.nan)
    df["dynamic_cost"] = dynamic_cost
    return df


def calc_deviation(
    df: pd.DataFrame,
    阈值窗口: int = 120,
    阈值最少样本: int = 60,
    低分位: float = 0.20,
    高分位: float = 0.80,
    低位默认值: float = -12.0,
    高位默认值: float = 25.0,
) -> pd.DataFrame:
    """价格相对递推成本偏离。"""
    valid = df["dynamic_cost"].notna() & (df["dynamic_cost"] > 0)
    df["deviation"] = np.nan
    df.loc[valid, "deviation"] = (df.loc[valid, "close"] / df.loc[valid, "dynamic_cost"] - 1) * 100

    low_th = (
        df["deviation"]
        .rolling(阈值窗口, min_periods=阈值最少样本)
        .quantile(低分位)
        .fillna(低位默认值)
        .clip(upper=-8.0)
    )
    high_th = (
        df["deviation"]
        .rolling(阈值窗口, min_periods=阈值最少样本)
        .quantile(高分位)
        .fillna(高位默认值)
        .clip(lower=15.0)
    )

    df["low_threshold"] = low_th
    df["high_threshold"] = high_th

    df["deep_discount_signal"] = (df["deviation"] < low_th) & (df["deviation"].shift(1) >= low_th.shift(1))
    df["overheat_signal"] = (df["deviation"] > high_th) & (df["deviation"].shift(1) <= high_th.shift(1))
    return df


def score_main_behavior(
    df: pd.DataFrame,
    回看天数: int = 60,
    拉升斜率阈值: float = 0.25,
    放弃偏离均值阈值: float = -18.0,
    放弃换手率阈值: float = 0.015,
) -> Dict[str, float]:
    """
    行为压力评分（0-100），不是概率。
    - lift_pressure: 拉升压力
    - abandon_risk: 放弃风险
    - recycle_activity: 滚动换手活跃度
    """
    recent = df.tail(回看天数).dropna(subset=["dynamic_cost", "deviation"]).copy()
    if recent.empty:
        return {"拉升压力": 0.0, "放弃风险": 0.0, "滚动换手活跃度": 0.0}

    below_ratio = float((recent["close"] < recent["dynamic_cost"]).mean())
    dev_min = float(recent["deviation"].min())
    dev_mean = float(recent["deviation"].mean())

    if len(recent) > 1:
        x = np.arange(len(recent))
        slope = float(np.polyfit(x, recent["deviation"], 1)[0])
    else:
        slope = 0.0

    recent_turnover = float(recent["effective_turnover"].tail(20).mean())

    lift_pressure = 0.0
    lift_pressure += min(below_ratio * 70, 45)
    lift_pressure += min(max(-dev_min - 8, 0) * 1.2, 35)
    lift_pressure += 20 if slope > 拉升斜率阈值 else 0

    abandon_risk = 0.0
    abandon_risk += 35 if below_ratio > 0.7 else 0
    abandon_risk += min(max(-slope, 0) * 25, 35)
    abandon_risk += 30 if (dev_mean < 放弃偏离均值阈值 and recent_turnover < 放弃换手率阈值) else 0

    recycle_activity = 0.0
    recycle_activity += min(recent_turnover * 1000, 40)
    recycle_activity += 25 if abs(dev_mean) < 6 else 0
    recycle_activity += 20 if abs(slope) < 0.15 else 0

    return {
        "拉升压力": round(min(lift_pressure, 100), 2),
        "放弃风险": round(min(abandon_risk, 100), 2),
        "滚动换手活跃度": round(min(recycle_activity, 100), 2),
    }


def calc_breakthrough_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """计算突破分析所需的衍生指标。"""
    df["volume_ma20"] = df["vol"].rolling(20, min_periods=10).mean()
    df["turnover_ma20"] = df["effective_turnover"].rolling(20, min_periods=10).mean()
    df["daily_amplitude"] = (df["high"] - df["low"]) / df["close"]
    df["amplitude_ma20"] = df["daily_amplitude"].rolling(20, min_periods=10).mean()
    df["price_low_20d"] = df["close"].rolling(20, min_periods=10).min()
    df["deviation_low_20d"] = df["deviation"].rolling(20, min_periods=10).min()
    return df


def detect_convergence_acceleration(
    df: pd.DataFrame,
    回看天数: int = 5,
) -> pd.DataFrame:
    """
    收敛加速: 偏离度负值但在加速收窄。
    偏离度变化率的一阶差分 > 0，说明折价修复在加速。
    """
    dev_change = df["deviation"] - df["deviation"].shift(回看天数)
    dev_accel = dev_change - dev_change.shift(回看天数)

    df["convergence_accel"] = (
        df["deviation"].lt(0)
        & dev_change.gt(0)
        & dev_accel.gt(0)
    ).fillna(False)
    return df


def detect_stealth_accumulation(
    df: pd.DataFrame,
    量比: float = 1.2,
    振幅比: float = 0.9,
) -> pd.DataFrame:
    """
    缩量吸筹: 成交量略高于均量，但振幅反而缩小。
    说明有人在打压价格的同时吃货，不愿引起市场注意。
    """
    vol_ok = df["vol"] > df["volume_ma20"] * 量比
    amp_tight = df["daily_amplitude"] < df["amplitude_ma20"] * 振幅比

    df["stealth_accumulation"] = (vol_ok & amp_tight).fillna(False)
    return df


def detect_deviation_divergence(
    df: pd.DataFrame,
    回看天数: int = 20,
) -> pd.DataFrame:
    """
    偏离度底背离: 价格创 N 日新低，但偏离度未同步新低。
    说明价格在跌但主力成本区有支撑，是吸筹完成的迹象。
    """
    price_new_low = df["close"].lt(df["price_low_20d"].shift(1))
    dev_not_new_low = df["deviation"].gt(df["deviation_low_20d"].shift(1))

    df["deviation_divergence"] = (price_new_low & dev_not_new_low).fillna(False)
    return df


def detect_underwater_consolidation(
    df: pd.DataFrame,
    连续天数: int = 5,
    偏离上限: float = -3.0,
    偏离下限: float = -8.0,
) -> pd.DataFrame:
    """
    水下蓄力: 偏离度在 [-8%, -3%] 窄幅震荡，且换手率温和。
    价格在成本线下不远的地方横向整理，主力在蓄力等待时机。
    """
    in_range = (
        df["deviation"].ge(偏离下限)
        & df["deviation"].le(偏离上限)
    ).fillna(False)

    consecutive = in_range.astype(int)
    streak = (consecutive.diff().ne(0)).cumsum()
    consecutive_count = consecutive.groupby(streak).cumsum()

    turnover_ok = df["effective_turnover"].gt(df["turnover_ma20"])

    df["underwater_consolidation"] = (
        consecutive_count.ge(连续天数) & turnover_ok
    ).fillna(False)
    return df


def detect_cost_convergence(
    df: pd.DataFrame,
    当前阈值: float = 3.0,
    前期阈值: float = 8.0,
    回看天数: int = 5,
) -> pd.DataFrame:
    """
    成本收敛: 价格距成本线快速收窄。
    N 天前偏离度 > 前期阈值, 当前 |偏离度| < 当前阈值。
    """
    near_cost = df["deviation"].abs().lt(当前阈值)
    was_far = df["deviation"].shift(回看天数).abs().gt(前期阈值)

    df["cost_convergence"] = (near_cost & was_far).fillna(False)
    return df


def apply_breakthrough_filters(
    df: pd.DataFrame,
    振幅异常倍数: float = 1.5,
    反弹过度百分比: float = 15.0,
) -> pd.DataFrame:
    """
    突破过滤器:
    - 振幅异常: 当日振幅 > N 倍均幅，可能冲顶而非突破
    - 反弹过度: 从 20 日低点已反弹 > M%，追高风险
    - 消息驱动: 偏离度从深水区 (<-15%) 到正值区用时 < 8 天
    """
    df["filter_amp_abnormal"] = df["daily_amplitude"] > df["amplitude_ma20"] * 振幅异常倍数

    df["filter_overextended"] = (
        (df["close"] / df["price_low_20d"] - 1) * 100 > 反弹过度百分比
    )

    min_dev_20d = df["deviation"].rolling(20, min_periods=10).min()
    deep_days = (df["deviation"].lt(-15)).astype(int)
    recovery_streak = deep_days.copy()
    reset_mask = df["deviation"].ge(0).fillna(True)
    for i in range(1, len(df)):
        if reset_mask.iloc[i]:
            recovery_streak.iloc[i] = 0
        elif deep_days.iloc[i] == 0:
            recovery_streak.iloc[i] = recovery_streak.iloc[i - 1] + 1
        else:
            recovery_streak.iloc[i] = 0
    df["filter_news_driven"] = (
        (df["deviation"] >= 0) & (recovery_streak.shift(1).lt(8) & recovery_streak.shift(1).gt(0))
    ).fillna(False)

    return df


def score_breakthrough(df: pd.DataFrame) -> pd.DataFrame:
    """
    吸筹驱动突破评分 (0-100)。
    - 收敛加速: 30 (最早信号，权重最高)
    - 缩量吸筹: 25 (区分吸筹/派发的关键)
    - 偏离度底背离: 20 (趋势转折确认)
    - 水下蓄力: 15 (筹码集中特征)
    - 成本收敛: 10 (辅助确认)
    - 振幅异常: -20 (过滤冲顶)
    - 反弹过度: -20 (过滤追高)
    """
    score = pd.Series(0.0, index=df.index, dtype=float)

    score += df["convergence_accel"].fillna(False).astype(float) * 30
    score += df["stealth_accumulation"].fillna(False).astype(float) * 25
    score += df["deviation_divergence"].fillna(False).astype(float) * 20
    score += df["underwater_consolidation"].fillna(False).astype(float) * 15
    score += df["cost_convergence"].fillna(False).astype(float) * 10

    score -= df["filter_amp_abnormal"].fillna(False).astype(float) * 20
    score -= df["filter_overextended"].fillna(False).astype(float) * 20
    score -= df["filter_news_driven"].fillna(False).astype(float) * 15

    df["breakthrough_score"] = score.clip(lower=0, upper=100).round(1)
    return df


def detect_breakthrough(
    df: pd.DataFrame,
    配置: dict,
) -> pd.DataFrame:
    """
    一站式吸筹突破检测:
    捕捉主力吸筹完成、即将拉升的时刻，而非突破后的追高确认。
    """
    df = calc_breakthrough_indicators(df)

    df = detect_convergence_acceleration(
        df, 回看天数=int(配置.get("收敛加速回看天数", 5))
    )
    df = detect_stealth_accumulation(
        df,
        量比=配置.get("缩量吸筹量比", 1.2),
        振幅比=配置.get("缩量吸筹振幅比", 0.9),
    )
    df = detect_deviation_divergence(
        df, 回看天数=int(配置.get("底背离回看天数", 20))
    )
    df = detect_underwater_consolidation(
        df,
        连续天数=int(配置.get("水下蓄力天数", 5)),
        偏离上限=配置.get("水下蓄力偏离上限", -3.0),
        偏离下限=配置.get("水下蓄力偏离下限", -8.0),
    )
    df = detect_cost_convergence(
        df,
        当前阈值=配置.get("成本收敛当前阈值", 3.0),
        前期阈值=配置.get("成本收敛前期阈值", 8.0),
        回看天数=int(配置.get("收敛加速回看天数", 5)),
    )
    df = apply_breakthrough_filters(
        df,
        振幅异常倍数=配置.get("振幅异常倍数", 1.5),
        反弹过度百分比=配置.get("反弹过度百分比", 15.0),
    )
    df = score_breakthrough(df)

    突破阈值 = 配置.get("突破强度阈值", 50)
    df["effective_breakthrough"] = (
        df["breakthrough_score"] >= 突破阈值
    ).fillna(False)

    return df


def evaluate_signal_forward_returns(
    df: pd.DataFrame,
    信号列: str,
    观察周期: Iterable[int] = (5, 10, 20),
) -> pd.DataFrame:
    """统计信号触发后的未来收益表现。"""
    rows = []
    signal_mask = df[信号列].fillna(False)

    for h in 观察周期:
        future_ret = df["close"].shift(-h) / df["close"] - 1
        sample = future_ret[signal_mask].dropna()
        if sample.empty:
            rows.append(
                {
                    "未来天数": h,
                    "样本数": 0,
                    "平均收益率(%)": np.nan,
                    "中位数收益率(%)": np.nan,
                    "胜率(%)": np.nan,
                }
            )
            continue

        rows.append(
            {
                "未来天数": h,
                "样本数": int(sample.shape[0]),
                "平均收益率(%)": round(sample.mean() * 100, 2),
                "中位数收益率(%)": round(sample.median() * 100, 2),
                "胜率(%)": round((sample > 0).mean() * 100, 2),
            }
        )

    return pd.DataFrame(rows)


def plot_cost_analysis(df: pd.DataFrame, 股票代码: str, 标题后缀: str = "") -> None:
    """绘制成本分析图。"""
    fig, axes = plt.subplots(3, 1, figsize=(14, 10), gridspec_kw={"height_ratios": [3, 1, 1]})

    ax1 = axes[0]
    ax1.plot(df.index, df["close"], color="black", linewidth=1.2, label="收盘价")
    ax1.plot(df.index, df["vwap"], color="tab:blue", linestyle="--", linewidth=1.2, label="静态成本(VWAP)")
    ax1.plot(df.index, df["dynamic_cost"], color="tab:red", linewidth=1.6, label="动态成本(换手递推)")

    deep_idx = df.index[df["deep_discount_signal"].fillna(False)]
    hot_idx = df.index[df["overheat_signal"].fillna(False)]
    breakthrough_idx = df.index[df.get("effective_breakthrough", pd.Series(False, index=df.index)).fillna(False)]
    ax1.scatter(deep_idx, df.loc[deep_idx, "close"], color="green", marker="^", s=45, label="深度低估信号")
    ax1.scatter(hot_idx, df.loc[hot_idx, "close"], color="purple", marker="v", s=45, label="过热信号")
    ax1.scatter(breakthrough_idx, df.loc[breakthrough_idx, "close"], color="orange", marker="o", s=60, label="有效突破信号", zorder=5)

    ax1.set_title(f"{股票代码} 成本分析 {标题后缀}")
    ax1.legend(loc="upper left")
    ax1.grid(True, alpha=0.3)

    ax2 = axes[1]
    ax2.plot(df.index, df["deviation"], color="tab:orange", linewidth=1.1, label="偏离度(%)")
    ax2.plot(df.index, df["low_threshold"], color="green", linestyle="--", alpha=0.8, label="低位阈值")
    ax2.plot(df.index, df["high_threshold"], color="purple", linestyle="--", alpha=0.8, label="高位阈值")
    ax2.axhline(y=0, color="gray", linewidth=1, alpha=0.5)
    ax2.set_ylabel("偏离度 %")
    ax2.legend(loc="upper left")
    ax2.grid(True, alpha=0.3)

    ax3 = axes[2]
    bar_colors = np.where(df["close"] >= df["open"], "red", "green")
    ax3.bar(df.index, df["vol"], color=bar_colors, alpha=0.55, label="成交量")
    ax3_twin = ax3.twinx()
    ax3_twin.plot(df.index, df["effective_turnover"] * 100, color="tab:blue", linewidth=1, label="有效换手率(%)")
    ax3.set_ylabel("成交量")
    ax3_twin.set_ylabel("换手率 %")
    ax3.grid(True, alpha=0.3)

    handles1, labels1 = ax3.get_legend_handles_labels()
    handles2, labels2 = ax3_twin.get_legend_handles_labels()
    ax3.legend(handles1 + handles2, labels1 + labels2, loc="upper left")

    plt.tight_layout()
    plt.show()


def analyze_stock(
    股票代码: str,
    开始日期: str,
    结束日期: str,
    年化资金成本: Optional[float] = None,
    建仓起始日期: Optional[str] = None,
    参数档位: str = "neutral",
    自定义参数: Optional[Dict[str, float]] = None,
    显示图表: bool = True,
) -> Optional[pd.DataFrame]:
    """完整分析流程。"""
    print(f"正在分析 {股票代码} ...")

    df = get_stock_data(股票代码, 开始日期, 结束日期)
    if df.empty:
        print("未获取到数据")
        return None

    print(f"数据获取成功，共 {len(df)} 个交易日")
    if (df["turnover_source"] == "proxy").all():
        print("提示: 未获取到官方换手率，已使用成交量代理换手率。")

    配置 = 获取参数配置(参数档位)
    if 自定义参数:
        配置.update(自定义参数)

    实际年化资金成本 = 配置["年化资金成本"] if 年化资金成本 is None else 年化资金成本
    print(f"参数档位: {参数档位} | 年化资金成本: {实际年化资金成本:.2%}")

    df = calc_vwap(df)
    df = calc_dynamic_cost(
        df,
        年化资金成本=实际年化资金成本,
        建仓起始日期=建仓起始日期,
        最小换手率=配置["最小换手率"],
        最大换手率=配置["最大换手率"],
    )
    df = calc_deviation(
        df,
        阈值窗口=int(配置["阈值窗口"]),
        阈值最少样本=int(配置["阈值最少样本"]),
        低分位=配置["低分位"],
        高分位=配置["高分位"],
        低位默认值=配置["低位默认值"],
        高位默认值=配置["高位默认值"],
    )

    scores = score_main_behavior(
        df,
        回看天数=int(配置["回看天数"]),
        拉升斜率阈值=配置["拉升斜率阈值"],
        放弃偏离均值阈值=配置["放弃偏离均值阈值"],
        放弃换手率阈值=配置["放弃换手率阈值"],
    )
    print("\n行为压力评分(0-100，非概率):")
    print(f"拉升压力: {scores['拉升压力']}")
    print(f"放弃风险: {scores['放弃风险']}")
    print(f"滚动换手活跃度: {scores['滚动换手活跃度']}")

    df = detect_breakthrough(df, 配置)
    breakthrough_signals = df[df["effective_breakthrough"].fillna(False)]
    if not breakthrough_signals.empty:
        last_bt = breakthrough_signals.iloc[-1]
        print(f"\n最近有效突破: {last_bt.name.strftime('%Y-%m-%d')} "
              f"(强度={last_bt['breakthrough_score']:.0f})")
        print(f"突破信号总数: {len(breakthrough_signals)}")
    else:
        print("\n近期无有效突破信号")

    valid_df = df.dropna(subset=["dynamic_cost", "deviation"])
    if valid_df.empty:
        print("动态成本尚无有效数据，请检查建仓起始日期和样本区间。")
        return df

    latest = valid_df.iloc[-1]
    print(f"\n最新交易日: {latest.name.strftime('%Y-%m-%d')}")
    print(f"收盘价: {latest['close']:.2f}")
    print(f"动态成本: {latest['dynamic_cost']:.2f}")
    print(f"偏离度: {latest['deviation']:.2f}%")
    print(f"有效换手率: {latest['effective_turnover'] * 100:.2f}%")

    discount_stats = evaluate_signal_forward_returns(df, "deep_discount_signal")
    overheat_stats = evaluate_signal_forward_returns(df, "overheat_signal")

    print("\n[深度低估信号] 未来收益统计:")
    print(discount_stats.to_string(index=False))
    print("\n[过热信号] 未来收益统计:")
    print(overheat_stats.to_string(index=False))

    breakthrough_stats = evaluate_signal_forward_returns(df, "effective_breakthrough")
    print("\n[有效突破信号] 未来收益统计:")
    print(breakthrough_stats.to_string(index=False))

    if 显示图表:
        title = f"(参数档位={参数档位}, 年化资金成本 {实际年化资金成本 * 100:.1f}%)"
        plot_cost_analysis(df, 股票代码, title)

    return df


def generate_trade_signals(df: pd.DataFrame, 深度低估窗口天数: int = 14) -> pd.DataFrame:
    """
    生成综合交易信号:
    买入条件: (偏离度<低估值阈值 或 深度低估信号14日内触发过) 且 出现有效突破
    """
    if df.empty or "low_threshold" not in df.columns or "effective_breakthrough" not in df.columns:
        raise ValueError("DataFrame 缺少必要列，请先运行 calc_deviation 和 detect_breakthrough")

    discount_window = (
        df["deep_discount_signal"]
        .fillna(False)
        .rolling(深度低估窗口天数, min_periods=1)
        .max()
        .astype(bool)
    )

    is_undervalued = df["deviation"].lt(df["low_threshold"]).fillna(False)

    valid_zone = is_undervalued | discount_window

    df["trade_buy_signal"] = (valid_zone & df["effective_breakthrough"].fillna(False))
    df["trade_sell_signal"] = df["overheat_signal"].fillna(False)
    df["trade_signal_zone"] = valid_zone.map({True: "低估区", False: ""})

    return df


def backtest_single_stock_signals(
    df: pd.DataFrame,
    股票代码: str = "",
    初始资金: float = 100000.0,
    手续费率: float = 0.0003,
    滑点率: float = 0.001,
) -> Dict[str, object]:
    """
    单股信号回测。

    规则:
    - 买入: T 日出现 trade_buy_signal, T+1 开盘满仓买入
    - 卖出: T 日出现 trade_sell_signal, T+1 开盘全部卖出
    - 仅允许单只股票单仓位，不构建投资组合
    """
    required_columns = {"open", "close", "trade_buy_signal"}
    missing_columns = required_columns - set(df.columns)
    if missing_columns:
        raise ValueError(f"缺少回测所需列: {sorted(missing_columns)}")

    backtest_df = df.copy().reset_index()
    if "trade_date" not in backtest_df.columns and "index" in backtest_df.columns:
        backtest_df = backtest_df.rename(columns={"index": "trade_date"})

    if "trade_date" not in backtest_df.columns:
        raise ValueError("缺少 trade_date 列，无法执行单股回测")

    backtest_df = backtest_df.sort_values("trade_date").reset_index(drop=True)
    if "trade_sell_signal" not in backtest_df.columns:
        backtest_df["trade_sell_signal"] = backtest_df.get("overheat_signal", False)

    backtest_df["trade_buy_signal"] = backtest_df["trade_buy_signal"].fillna(False)
    backtest_df["trade_sell_signal"] = backtest_df["trade_sell_signal"].fillna(False)

    cash = float(初始资金)
    shares = 0
    entry_price = None
    entry_date = None
    pending_buy = False
    pending_sell = False

    trade_rows = []
    nav_rows = []

    for _, row in backtest_df.iterrows():
        trade_date = row["trade_date"]
        date_str = trade_date.strftime("%Y%m%d") if hasattr(trade_date, "strftime") else str(trade_date)
        open_price = float(row["open"]) if pd.notna(row["open"]) else float(row["close"])
        close_price = float(row["close"])

        if pending_sell and shares > 0:
            sell_price = open_price * (1 - 滑点率)
            gross_amount = sell_price * shares
            sell_fee = gross_amount * 手续费率
            cash += gross_amount - sell_fee
            hold_days = 0
            if entry_date is not None:
                hold_days = (
                    pd.Timestamp(trade_date) - pd.Timestamp(entry_date)
                ).days
            profit_pct = ((sell_price - entry_price) / entry_price * 100) if entry_price else 0.0

            trade_rows.append(
                {
                    "date": date_str,
                    "stock_code": 股票代码,
                    "type": "SELL",
                    "price": round(sell_price, 4),
                    "shares": int(shares),
                    "amount": round(gross_amount, 2),
                    "fee": round(sell_fee, 2),
                    "profit_pct": round(profit_pct, 2),
                    "hold_days": int(hold_days),
                    "reason": "过热卖出",
                }
            )
            shares = 0
            entry_price = None
            entry_date = None

        if pending_buy and shares == 0:
            buy_price = open_price * (1 + 滑点率)
            shares_to_buy = int(cash / (buy_price * (1 + 手续费率)) / 100) * 100
            if shares_to_buy >= 100:
                gross_amount = buy_price * shares_to_buy
                buy_fee = gross_amount * 手续费率
                total_cost = gross_amount + buy_fee
                cash -= total_cost
                shares = shares_to_buy
                entry_price = buy_price
                entry_date = trade_date

                trade_rows.append(
                    {
                        "date": date_str,
                        "stock_code": 股票代码,
                        "type": "BUY",
                        "price": round(buy_price, 4),
                        "shares": int(shares),
                        "amount": round(total_cost, 2),
                        "fee": round(buy_fee, 2),
                        "profit_pct": np.nan,
                        "hold_days": np.nan,
                        "reason": "成本突破买入",
                    }
                )

        next_buy = bool(row["trade_buy_signal"]) and shares == 0
        next_sell = bool(row["trade_sell_signal"]) and shares > 0

        market_value = shares * close_price
        total_equity = cash + market_value
        nav_rows.append(
            {
                "date": date_str,
                "nav": round(total_equity / 初始资金, 6) if 初始资金 else np.nan,
                "cash": round(cash, 2),
                "market_value": round(market_value, 2),
                "total_equity": round(total_equity, 2),
                "position_held": shares > 0,
                "holding_shares": int(shares),
                "current_price": round(close_price, 4),
                "entry_price": round(entry_price, 4) if entry_price is not None else np.nan,
                "buy_signal": bool(row["trade_buy_signal"]),
                "sell_signal": bool(row["trade_sell_signal"]),
                "pending_buy_next_open": next_buy,
                "pending_sell_next_open": next_sell,
            }
        )

        pending_buy = next_buy
        pending_sell = next_sell

    nav_df = pd.DataFrame(nav_rows)
    trades_df = pd.DataFrame(
        trade_rows,
        columns=[
            "date",
            "stock_code",
            "type",
            "price",
            "shares",
            "amount",
            "fee",
            "profit_pct",
            "hold_days",
            "reason",
        ],
    )

    final_nav = float(nav_df["nav"].iloc[-1]) if not nav_df.empty else 1.0
    return {
        "nav_history": nav_df,
        "trades": trades_df,
        "final_nav": final_nav,
        "total_return_pct": (final_nav - 1.0) * 100,
    }


def save_single_stock_backtest_chart(
    df: pd.DataFrame,
    nav_df: pd.DataFrame,
    图表输出路径: str,
    股票代码: str = "",
) -> str:
    """保存单股回测净值图，包含策略净值和个股收盘价折线。"""
    chart_df = df.copy().reset_index()
    if "trade_date" not in chart_df.columns and "index" in chart_df.columns:
        chart_df = chart_df.rename(columns={"index": "trade_date"})
    if "trade_date" not in chart_df.columns:
        raise ValueError("缺少 trade_date 列，无法绘制回测图表")

    chart_df["date"] = pd.to_datetime(chart_df["trade_date"])
    plot_df = nav_df.copy()
    plot_df["date"] = pd.to_datetime(plot_df["date"], format="%Y%m%d", errors="coerce")
    plot_df = plot_df.merge(
        chart_df[["date", "close", "trade_buy_signal", "trade_sell_signal"]],
        on="date",
        how="left",
    )

    fig = Figure(figsize=(14, 8))
    FigureCanvasAgg(fig)
    ax_nav = fig.add_subplot(111)
    ax_price = ax_nav.twinx()

    ax_nav.plot(
        plot_df["date"],
        plot_df["nav"],
        color="tab:blue",
        linewidth=2.0,
        label="策略净值",
    )
    ax_nav.axhline(y=1.0, color="gray", linestyle="--", linewidth=1.0, alpha=0.7, label="净值起点")

    ax_price.plot(
        plot_df["date"],
        plot_df["close"],
        color="tab:orange",
        linewidth=1.5,
        alpha=0.9,
        label="个股收盘价",
    )

    buy_points = plot_df[plot_df["trade_buy_signal"].fillna(False)]
    sell_points = plot_df[plot_df["trade_sell_signal"].fillna(False)]
    if not buy_points.empty:
        ax_price.scatter(
            buy_points["date"],
            buy_points["close"],
            color="green",
            marker="^",
            s=60,
            label="买入信号",
            zorder=5,
        )
    if not sell_points.empty:
        ax_price.scatter(
            sell_points["date"],
            sell_points["close"],
            color="red",
            marker="v",
            s=60,
            label="卖出信号",
            zorder=5,
        )

    final_nav = float(plot_df["nav"].iloc[-1]) if not plot_df.empty else 1.0
    final_close = float(plot_df["close"].iloc[-1]) if not plot_df.empty else np.nan
    title = f"{股票代码 or '单股'} 回测净值与收盘价"
    ax_nav.set_title(title)
    ax_nav.set_xlabel("日期")
    ax_nav.set_ylabel("策略净值", color="tab:blue")
    ax_price.set_ylabel("收盘价", color="tab:orange")
    ax_nav.tick_params(axis="y", labelcolor="tab:blue")
    ax_price.tick_params(axis="y", labelcolor="tab:orange")
    ax_nav.grid(True, alpha=0.25)

    stats_text = (
        f"最终净值: {final_nav:.4f}\n"
        f"累计收益: {(final_nav - 1.0) * 100:.2f}%\n"
        f"最新收盘价: {final_close:.2f}"
    )
    ax_nav.text(
        0.02,
        0.98,
        stats_text,
        transform=ax_nav.transAxes,
        va="top",
        fontsize=10,
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.85),
    )

    handles_nav, labels_nav = ax_nav.get_legend_handles_labels()
    handles_price, labels_price = ax_price.get_legend_handles_labels()
    ax_nav.legend(handles_nav + handles_price, labels_nav + labels_price, loc="upper left")

    fig.tight_layout()
    fig.savefig(图表输出路径, dpi=150, bbox_inches="tight")
    return 图表输出路径


def export_trade_signal_csv(
    df: pd.DataFrame,
    输出路径: str,
    股票代码: str = "",
    执行回测: bool = True,
    初始资金: float = 100000.0,
    手续费率: float = 0.0003,
    滑点率: float = 0.001,
    净值输出路径: Optional[str] = None,
    交易明细输出路径: Optional[str] = None,
    图表输出路径: Optional[str] = None,
) -> str:
    """
    导出交易信号 CSV 供回测策略使用。
    格式: date, price, signal
    """
    if "trade_buy_signal" not in df.columns:
        raise ValueError("请先运行 generate_trade_signals")

    export_df = df.reset_index()
    if "trade_date" not in export_df.columns and "index" in export_df.columns:
        export_df = export_df.rename(columns={"index": "trade_date"})
    export_df["date"] = export_df["trade_date"].dt.strftime("%Y%m%d")
    export_df["signal"] = ""
    export_df["trade_buy_signal"] = export_df["trade_buy_signal"].fillna(False)
    export_df["trade_sell_signal"] = export_df.get(
        "trade_sell_signal",
        export_df.get("overheat_signal", False),
    )
    if not isinstance(export_df["trade_sell_signal"], pd.Series):
        export_df["trade_sell_signal"] = False
    export_df["trade_sell_signal"] = export_df["trade_sell_signal"].fillna(False)

    buy_mask = export_df["trade_buy_signal"]
    sell_mask = export_df["trade_sell_signal"]
    export_df.loc[buy_mask, "signal"] = "成本突破买入"
    export_df.loc[sell_mask, "signal"] = np.where(
        export_df.loc[sell_mask, "signal"].eq(""),
        "成本过热卖出",
        export_df.loc[sell_mask, "signal"] + "|成本过热卖出",
    )

    cols = [
        "date",
        "open",
        "close",
        "deviation",
        "low_threshold",
        "high_threshold",
        "breakthrough_score",
        "trade_buy_signal",
        "trade_sell_signal",
        "signal",
    ]
    available = [c for c in cols if c in export_df.columns]
    export_df[available].to_csv(输出路径, index=False, encoding="utf-8-sig")

    buy_count = export_df["signal"].str.contains("买入").sum()
    sell_count = export_df["signal"].str.contains("卖出").sum()
    print(f"信号已导出: {输出路径} (买入信号={buy_count}个, 卖出信号={sell_count}个)")

    if 执行回测:
        if 净值输出路径 is None:
            if 输出路径.endswith("_trade_signals.csv"):
                净值输出路径 = 输出路径.replace("_trade_signals.csv", "_nav_history.csv")
            else:
                净值输出路径 = os.path.splitext(输出路径)[0] + "_nav_history.csv"

        if 交易明细输出路径 is None:
            if 输出路径.endswith("_trade_signals.csv"):
                交易明细输出路径 = 输出路径.replace("_trade_signals.csv", "_backtest_trades.csv")
            else:
                交易明细输出路径 = os.path.splitext(输出路径)[0] + "_backtest_trades.csv"

        if 图表输出路径 is None:
            if 输出路径.endswith("_trade_signals.csv"):
                图表输出路径 = 输出路径.replace("_trade_signals.csv", "_nav_curve.png")
            else:
                图表输出路径 = os.path.splitext(输出路径)[0] + "_nav_curve.png"

        backtest_result = backtest_single_stock_signals(
            df=df,
            股票代码=股票代码,
            初始资金=初始资金,
            手续费率=手续费率,
            滑点率=滑点率,
        )
        backtest_result["nav_history"].to_csv(净值输出路径, index=False, encoding="utf-8-sig")
        backtest_result["trades"].to_csv(交易明细输出路径, index=False, encoding="utf-8-sig")
        save_single_stock_backtest_chart(
            df=df,
            nav_df=backtest_result["nav_history"],
            图表输出路径=图表输出路径,
            股票代码=股票代码,
        )

        print(
            f"单股回测完成: {股票代码 or os.path.basename(输出路径)} | "
            f"最终净值={backtest_result['final_nav']:.4f} | "
            f"累计收益={backtest_result['total_return_pct']:.2f}%"
        )
        print(f"净值已导出: {净值输出路径}")
        print(f"交易明细已导出: {交易明细输出路径}")
        print(f"回测图已导出: {图表输出路径}")

    return 输出路径


def batch_generate_signals(
    股票列表: list,
    开始日期: str,
    结束日期: str,
    建仓起始日期: str = None,
    参数档位: str = "neutral",
    输出目录: str = "strategy/trade_signals",
) -> dict:
    """
    批量生成交易信号，每个股票一个 CSV 文件。
    返回 {股票代码: 文件路径} 字典。
    """
    import os
    os.makedirs(输出目录, exist_ok=True)

    结果 = {}
    for i, 股票代码 in enumerate(股票列表):
        try:
            print(f"[{i+1}/{len(股票列表)}] 处理 {股票代码} ...")
            df = get_stock_data(股票代码, 开始日期, 结束日期)
            if df.empty:
                print(f"  {股票代码} 无数据，跳过")
                continue

            配置 = 获取参数配置(参数档位)

            df = calc_vwap(df)
            df = calc_dynamic_cost(
                df,
                年化资金成本=配置["年化资金成本"],
                建仓起始日期=建仓起始日期,
                最小换手率=配置["最小换手率"],
                最大换手率=配置["最大换手率"],
            )
            df = calc_deviation(
                df,
                阈值窗口=int(配置["阈值窗口"]),
                阈值最少样本=int(配置["阈值最少样本"]),
                低分位=配置["低分位"],
                高分位=配置["高分位"],
                低位默认值=配置["低位默认值"],
                高位默认值=配置["高位默认值"],
            )
            df = detect_breakthrough(df, 配置)
            df = generate_trade_signals(df)

            输出路径 = os.path.join(输出目录, f"{股票代码.replace('.', '_')}_trade_signals.csv")
            export_trade_signal_csv(df, 输出路径, 股票代码, 执行回测=False)
            结果[股票代码] = 输出路径
        except Exception as e:
            print(f"  {股票代码} 处理失败: {str(e)}")
            continue

    return 结果


if __name__ == "__main__":
    ts.set_token(TUSHARE_TOKEN)
    symbol = '002317.SZ'
    # symbol = '002310.SZ'
    # symbol = '000716.SZ'
    # symbol = '002457.SZ'
    # symbol = '002342.SZ'
    # symbol = '002317.SZ'
    # symbol = '000518.SZ'
    # symbol = '002242.SZ'
    # symbol = '600522.SH'
    # symbol = '600722.SH'
    # symbol = '600522.SH'
    # symbol = '600488.SH'
    # symbol = '600855.SH'
    symbol = '001366.SZ'
    symbol = '002354.SZ'
    symbol = '600699.SH'
    # 单股分析 + 图表
    df_result = analyze_stock(
        股票代码=symbol,
        开始日期="20240101",
        结束日期="20260529",
        年化资金成本=None,
        建仓起始日期="20240301",
        参数档位="neutral",
        显示图表=True,
    )

    if df_result is not None:
        df_result.to_csv(f"{symbol.split('.')[0]}_cost_analysis.csv", encoding="utf-8-sig")
        df_result = generate_trade_signals(df_result)
        export_trade_signal_csv(
            df_result,
            f"{symbol.split('.')[0]}_trade_signals.csv",
            股票代码=symbol,
        )

    # 批量生成交易信号（供回测使用）
    # 股票池 = ["002317.SZ", "002623.SZ", "600519.SH", "000858.SZ"]
    # batch_generate_signals(
    #     股票列表=股票池,
    #     开始日期="20240101",
    #     结束日期="20260518",
    #     建仓起始日期="20240301",
    #     参数档位="neutral",
    #     输出目录="strategy/trade_signals",
    # )
