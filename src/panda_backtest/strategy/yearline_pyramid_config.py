#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
年线锚定式金字塔仓位管理策略 - 配置文件

包含：
1. 区间配置（Zone Configuration）：定义偏离度区间和对应的仓位比例
2. 再平衡配置（Rebalance Configuration）：定义再平衡触发条件
3. 股票分组映射（Stock Group Mapping）：将股票分配到不同的配置组合
"""

# ============================================================================
# 区间配置定义
# ============================================================================
"""
区间配置结构：
{
    'name': '配置名称',
    'description': '配置描述',
    'zones': {
        zone_id: {
            'range': (min_deviation, max_deviation),  # 偏离度范围
            'ratio': target_position_ratio             # 目标仓位比例
        }
    }
}

偏离度 = (现价 - MA220) / MA220
"""
# ZONE_CONFIGS = {
#     # 配置1：
#     'zone_config_1': {
#         'name': '激进型区间配置',
#         'description': '',
#         'zones': {
#             -4: {'range': (-1000, -0.25), 'ratio': 0.05},
#             -3: {'range': (-0.25, -0.17), 'ratio': 0.045},
#             -2: {'range': (-0.17, -0.10), 'ratio': 0.04},
#             -1: {'range': (-0.10, -0.02), 'ratio': 0.035},
#             0: {'range': (-0.02, 0.05), 'ratio': 0.03},
#             1: {'range': (0.05, 0.15), 'ratio': 0.025},
#             2: {'range': (0.15, 0.25), 'ratio': 0.02},
#             3: {'range': (0.25, 0.35), 'ratio': 0.015},
#             4: {'range': (0.35, 0.45), 'ratio': 0.01},
#             5: {'range': (0.45, 1000), 'ratio': 0.005},
#         }
#     },
#     # 配置2：
#     'zone_config_2': {
#         'name': '平衡型区间配置',
#         'description': '',
#         'zones': {
#             -4: {'range': (-1000, -0.20), 'ratio': 0.05},
#             -3: {'range': (-0.20, -0.15), 'ratio': 0.045},
#             -2: {'range': (-0.15, -0.10), 'ratio': 0.04},
#             -1: {'range': (-0.10, -0.05), 'ratio': 0.035},
#             0: {'range': (-0.05, 0.00), 'ratio': 0.03},
#             1: {'range': (0.00, 0.10), 'ratio': 0.025},
#             2: {'range': (0.10, 0.20), 'ratio': 0.02},
#             3: {'range': (0.20, 0.30), 'ratio': 0.015},
#             4: {'range': (0.30, 0.35), 'ratio': 0.01},
#             5: {'range': (0.35, 1000), 'ratio': 0.005},
#         }
#     },
# }


# ZONE_CONFIGS = {
#     # 配置1：
#     'zone_config_1': {
#         'name': '激进型区间配置',
#         'description': '',
#         'zones': {
#             -4: {'range': (-1000, -0.25), 'ratio': 0.05},
#             -3: {'range': (-0.25, -0.17), 'ratio': 0.045},
#             -2: {'range': (-0.17, -0.10), 'ratio': 0.041},
#             -1: {'range': (-0.10, -0.02), 'ratio': 0.037},
#             0: {'range': (-0.02, 0.05), 'ratio': 0.033},
#             1: {'range': (0.05, 0.15), 'ratio': 0.028},
#             2: {'range': (0.15, 0.25), 'ratio': 0.024},
#             3: {'range': (0.25, 0.35), 'ratio': 0.02},
#             4: {'range': (0.35, 0.45), 'ratio': 0.016},
#             5: {'range': (0.45, 0.50), 'ratio': 0.013},
#             6: {'range': (0.50, 1000), 'ratio': 0.009},
#         }
#     },
#     # 配置2：
#     'zone_config_2': {
#         'name': '平衡型区间配置',
#         'description': '',
#         'zones': {
#             -4: {'range': (-1000, -0.20), 'ratio': 0.05},
#             -3: {'range': (-0.20, -0.15), 'ratio': 0.045},
#             -2: {'range': (-0.15, -0.10), 'ratio': 0.041},
#             -1: {'range': (-0.10, -0.05), 'ratio': 0.037},
#             0: {'range': (-0.05, 0.00), 'ratio': 0.033},
#             1: {'range': (0.00, 0.10), 'ratio': 0.028},
#             2: {'range': (0.10, 0.20), 'ratio': 0.024},
#             3: {'range': (0.20, 0.30), 'ratio': 0.02},
#             4: {'range': (0.30, 0.35), 'ratio': 0.016},
#             5: {'range': (0.35, 0.40), 'ratio': 0.013},
#             6: {'range': (0.40, 1000), 'ratio': 0.009},
#         }
#     },
# }
ZONE_CONFIGS = {
    # 配置1：
    'zone_config_1': {
        'name': '激进型区间配置',
        'description': '',
        'zones': {
            -4: {'range': (-1000, -0.25), 'ratio': 0.05},
            -3: {'range': (-0.25, -0.17), 'ratio': 0.045},
            -2: {'range': (-0.17, -0.10), 'ratio': 0.041},
            -1: {'range': (-0.10, -0.02), 'ratio': 0.037},
            0: {'range': (-0.02, 0.05), 'ratio': 0.031},
            1: {'range': (0.05, 0.15), 'ratio': 0.026},
            2: {'range': (0.15, 0.25), 'ratio': 0.021},
            3: {'range': (0.25, 0.35), 'ratio': 0.017},
            4: {'range': (0.35, 0.45), 'ratio': 0.012},
            5: {'range': (0.45, 0.50), 'ratio': 0.008},
            6: {'range': (0.50, 1000), 'ratio': 0.006},
        }
    },
    # 配置2：
    'zone_config_2': {
        'name': '平衡型区间配置',
        'description': '',
        'zones': {
            -3: {'range': (-1000, -0.20), 'ratio': 0.05},
            -2: {'range': (-0.20, -0.15), 'ratio': 0.045},
            -1: {'range': (-0.15, -0.10), 'ratio': 0.041},
            0: {'range': (-0.10, 0.00), 'ratio': 0.031},
            1: {'range': (0.0, 0.07), 'ratio': 0.021},
            2: {'range': (0.07, 0.15), 'ratio': 0.012},
            3: {'range': (0.15, 1000), 'ratio': 0},
        }
    },
}

# ============================================================================
# 自动权重系数配置定义
# ============================================================================
"""
自动权重系数配置结构：
{
    'name': '配置名称',
    'description': '配置描述',
    'weight_zones': [
        {'range': (min_deviation, max_deviation), 'weight_bonus': 权重加成}
    ]
}

根据均线偏离度自动调整权重系数，偏离度越低（越便宜），权重加成越高
"""

# AUTO_WEIGHT_CONFIGS = {
#     # 1号配置：适合波动较大的股票
#     'auto_weight_config_1': {
#         'name': '1号自动权重配置',
#         'description': '适合波动较大的股票，偏离度区间较宽',
#         'weight_zones': [
#             {'range': (-1000, -0.25), 'weight_bonus': 0.4},   # -25%以下 权重+0.4
#             {'range': (-0.25, -0.18), 'weight_bonus': 0.3},   # -18%到-25% 权重+0.3
#             {'range': (-0.18, -0.10), 'weight_bonus': 0.2},   # -10%到-18% 权重+0.2
#             {'range': (-0.10, 0.00), 'weight_bonus': 0.1},    # 0到-10% 权重+0.1
#             {'range': (0.00, 0.10), 'weight_bonus': 0.1},     # 0到10% 权重+0.1
#             {'range': (0.10, 1000), 'weight_bonus': 0.0},     # 10%以上 无加成
#         ]
#     },
#
#     # 2号配置：适合波动较小的股票
#     'auto_weight_config_2': {
#         'name': '2号自动权重配置',
#         'description': '适合波动较小的股票，偏离度区间较窄',
#         'weight_zones': [
#             {'range': (-1000, -0.20), 'weight_bonus': 0.4},   # -20%以下 权重+0.4
#             {'range': (-0.20, -0.15), 'weight_bonus': 0.3},   # -15%到-20% 权重+0.3
#             {'range': (-0.15, -0.10), 'weight_bonus': 0.2},   # -10%到-15% 权重+0.2
#             {'range': (-0.10, 0.00), 'weight_bonus': 0.1},    # 0到-10% 权重+0.1
#             {'range': (0.00, 0.10), 'weight_bonus': 0.1},     # 0到10% 权重+0.1
#             {'range': (0.10, 1000), 'weight_bonus': 0.0},     # 10%以上 无加成
#         ]
#     },
# }

# AUTO_WEIGHT_CONFIGS = {
#     # 1号配置：适合波动较大的股票
#     'auto_weight_config_1': {
#         'name': '1号自动权重配置',
#         'description': '适合波动较大的股票，偏离度区间较宽',
#         'weight_zones': [
#             {'range': (-1000, -0.15), 'weight_bonus': 0.4},  # -25%以下 权重+0.4
#             {'range': (-0.15, -0.05), 'weight_bonus': 0.3},  # -18%到-25% 权重+0.3
#             {'range': (-0.05, 0.05), 'weight_bonus': 0.2},  # 0到-10% 权重+0.1
#             {'range': (0.05, 0.15), 'weight_bonus': 0.1},  # 0到10% 权重+0.1
#             {'range': (0.15, 1000), 'weight_bonus': 0.0},  # 10%以上 无加成
#         ]
#     },
#
#     # 2号配置：适合波动较小的股票
#     'auto_weight_config_2': {
#         'name': '2号自动权重配置',
#         'description': '适合波动较小的股票，偏离度区间较窄',
#         'weight_zones': [
#             {'range': (-1000, -0.15), 'weight_bonus': 0.4},  # -25%以下 权重+0.4
#             {'range': (-0.15, -0.05), 'weight_bonus': 0.3},  # -18%到-25% 权重+0.3
#             {'range': (-0.05, 0.05), 'weight_bonus': 0.2},  # 0到-10% 权重+0.1
#             {'range': (0.05, 0.15), 'weight_bonus': 0.1},  # 0到10% 权重+0.1
#             {'range': (0.15, 1000), 'weight_bonus': 0.0},  # 10%以上 无加成
#         ]
#     },
# }


AUTO_WEIGHT_CONFIGS = {
    # 1号配置：适合波动较大的股票
    'auto_weight_config_1': {
        'name': '1号自动权重配置',
        'description': '适合波动较大的股票，偏离度区间较宽',
        'weight_zones': [
            {'range': (-1000, -0.25), 'weight_bonus': 0.30},  # -25%以下 权重+0.4
            {'range': (-0.25, -0.20), 'weight_bonus': 0.25},  # -18%到-25% 权重+0.3
            {'range': (-0.20, -0.1), 'weight_bonus': 0.20},  # 0到-10% 权重+0.1
            {'range': (-0.10, 0), 'weight_bonus': 0.10},  # 0到-10% 权重+0.1
            {'range': (0.00, 0.1), 'weight_bonus': 0.05},  # 0到10% 权重+0.1
            {'range': (0.1, 1000), 'weight_bonus': 0.0},  # 10%以上 无加成
        ]
    },

    # 2号配置：适合波动较小的股票
    'auto_weight_config_2': {
        'name': '2号自动权重配置',
        'description': '适合波动较小的股票，偏离度区间较窄',
        'weight_zones': [
            {'range': (-1000, -0.25), 'weight_bonus': 0.30},  # -25%以下 权重+0.4
            {'range': (-0.25, -0.20), 'weight_bonus': 0.25},  # -18%到-25% 权重+0.3
            {'range': (-0.20, -0.1), 'weight_bonus': 0.20},  # 0到-10% 权重+0.1
            {'range': (-0.10, 0), 'weight_bonus': 0.10},  # 0到-10% 权重+0.1
            {'range': (0.00, 0.1), 'weight_bonus': 0.05},  # 0到10% 权重+0.1
            {'range': (0.1, 1000), 'weight_bonus': 0.0},  # 10%以上 无加成
        ]
    },
}

# ============================================================================
# 再平衡配置定义
# ============================================================================
"""
再平衡配置结构：
{
    'name': '配置名称',
    'description': '配置描述',
    'rebalance_threshold': 相对偏离率阈值,  # 当相对偏离率超过此值时触发再平衡
    'min_trade_amount': 最小交易金额,       # 单次交易金额低于此值不交易
    'min_trade_shares': 最小交易股数,       # 调整股数低于此值不交易
}

相对偏离率 = (当前仓位 - 目标仓位) / 目标仓位
"""

REBALANCE_CONFIGS = {
    # 配置1
    'rebalance_config_1': {
        'name': '激进再平衡配置',
        'description': '阈值低，频繁调整，适合主动管理的投资者',
        'rebalance_threshold': 0.12,  # 10% 相对偏离率
        # 'rebalance_threshold': 1,  # 10% 相对偏离率
        'min_trade_amount': 5000,      # 最小交易金额 2000元
        'min_trade_shares': 100,        # 最小交易股数 50股
    },

    # 配置2
    'rebalance_config_2': {
        'name': '保守再平衡配置',
        'description': '阈值高，少量调整，适合被动管理的投资者',
        'rebalance_threshold': 0.30,  # 30% 相对偏离率
        'min_trade_amount': 5000,      # 最小交易金额 5000元
        'min_trade_shares': 100,       # 最小交易股数 100股
    },

    # 配置3
    'rebalance_config_3': {
        'name': '平衡再平衡配置',
        'description': '阈值适中，适度调整，适合大多数投资者',
        'rebalance_threshold': 0.20,  # 20% 相对偏离率
        'min_trade_amount': 3000,      # 最小交易金额 3000元
        'min_trade_shares': 100,       # 最小交易股数 100股
    },
}

# ============================================================================
# 股票分组映射
# ============================================================================
"""
股票分组映射结构：
{
    'group_name': {
        'stocks': [股票代码列表],
        'zone_config': '使用的区间配置名称',
        'rebalance_config': '使用的再平衡配置名称',
        'weight': 权重系数（可选，默认1.0）
    }
}
"""

STOCK_GROUP_MAPPING = {
    # 分组A：中文在线分组
    # 'group_A': {
    #     'name': '中文在线分组',
    #     'description': '中等波动性股票，采用平衡型区间和再平衡配置',
    #     'stocks': ['300364.SZ'],
    #     'zone_config': 'zone_config_1',
    #     'rebalance_config': 'rebalance_config_3',
    #     'weight': 1.0,
    #     'auto_weight_config': 'auto_weight_config_1',  # 使用1号自动权重配置
    # },
    # 分组B
    'group_B': {
        'name': '激进型股票分组',
        'description': '高波动性股票，采用激进型区间和再平衡配置',
        'stocks': ['600600.SH',  # 青岛啤酒
                   '600690.SH',  # 海尔智家
                   '601336.SH',  # 新华保险

                   '600900.SH',  # 长江电力
                   '600919.SH',  # 江苏银行
                   '600660.SH',  # 福耀玻璃

                   '600535.SH',  # 天士力

                   '002241.SZ',  # 歌尔股份
                   '000568.SZ',  # 泸州老窖
                   '000963.SZ',  # 华东医药
                   ],
        #  python calc_adjusted_price_ma.py --symbol 600600.SH --start_date 20210101  --end_date 20251101
        'zone_config': 'zone_config_2',
        'rebalance_config': 'rebalance_config_1',
        'weight': 1,
        'auto_weight_config': 'auto_weight_config_2',  # 使用2号自动权重配置
    },


}

# ============================================================================
# 辅助函数
# ============================================================================

def get_stock_config(stock_id):
    """
    根据股票代码获取其对应的区间配置和再平衡配置
    
    Args:
        stock_id: 股票代码
        
    Returns:
        tuple: (zone_config_name, rebalance_config_name, weight, auto_weight_config_name)
    """
    for group_name, group_info in STOCK_GROUP_MAPPING.items():
        # if stock_id in group_info['stocks']:
        return (
            group_info['zone_config'],
            group_info['rebalance_config'],
            group_info.get('weight', 0.2),
            group_info.get('auto_weight_config', None)
        )
    
    # 如果未找到，返回默认配置（平衡型）
    return ('zone_config_2', 'rebalance_config_1', 1.0, None)


def get_zone_config(config_name):
    """获取区间配置"""
    return ZONE_CONFIGS.get(config_name)


def get_rebalance_config(config_name):
    """获取再平衡配置"""
    return REBALANCE_CONFIGS.get(config_name)


def get_auto_weight_config(config_name):
    """获取自动权重配置"""
    return AUTO_WEIGHT_CONFIGS.get(config_name)


def calculate_auto_weight(deviation, auto_weight_config_name):
    """
    根据均线偏离度计算自动权重加成
    
    Args:
        deviation: 均线偏离度 (现价 - MA220) / MA220
        auto_weight_config_name: 自动权重配置名称
        
    Returns:
        float: 权重加成值，如果配置不存在则返回0
    """
    if not auto_weight_config_name:
        return 0.0
    
    config = AUTO_WEIGHT_CONFIGS.get(auto_weight_config_name)
    if not config:
        return 0.0
    
    for zone in config['weight_zones']:
        min_dev, max_dev = zone['range']
        if min_dev <= deviation < max_dev:
            return zone['weight_bonus']
    
    return 0.0


def get_effective_weight(stock_id, deviation):
    """
    获取股票的有效权重（基础权重 + 自动权重加成）
    
    Args:
        stock_id: 股票代码
        deviation: 当前均线偏离度
        
    Returns:
        float: 有效权重
    """
    zone_config, rebalance_config, base_weight, auto_weight_config = get_stock_config(stock_id)
    weight_bonus = calculate_auto_weight(deviation, auto_weight_config)
    return base_weight + weight_bonus


def validate_configs():
    """验证配置的有效性"""
    errors = []
    
    # 验证区间配置
    for config_name, config in ZONE_CONFIGS.items():
        if 'zones' not in config:
            errors.append(f"区间配置 {config_name} 缺少 'zones' 字段")
        else:
            for zone_id, zone_info in config['zones'].items():
                if 'range' not in zone_info or 'ratio' not in zone_info:
                    errors.append(f"区间配置 {config_name} 的区间 {zone_id} 缺少必要字段")
    
    # 验证再平衡配置
    for config_name, config in REBALANCE_CONFIGS.items():
        required_fields = ['rebalance_threshold', 'min_trade_amount', 'min_trade_shares']
        for field in required_fields:
            if field not in config:
                errors.append(f"再平衡配置 {config_name} 缺少 '{field}' 字段")

    # 验证股票分组映射
    for group_name, group_info in STOCK_GROUP_MAPPING.items():
        zone_config = group_info.get('zone_config')
        rebalance_config = group_info.get('rebalance_config')
        
        if zone_config not in ZONE_CONFIGS:
            errors.append(f"股票分组 {group_name} 引用的区间配置 {zone_config} 不存在")
        
        if rebalance_config not in REBALANCE_CONFIGS:
            errors.append(f"股票分组 {group_name} 引用的再平衡配置 {rebalance_config} 不存在")
    
    return errors


if __name__ == '__main__':
    # 验证配置
    errors = validate_configs()
    if errors:
        print("配置验证失败：")
        for error in errors:
            print(f"  - {error}")
    else:
        print("配置验证成功！")
        print(f"\n区间配置数量: {len(ZONE_CONFIGS)}")
        print(f"再平衡配置数量: {len(REBALANCE_CONFIGS)}")
        print(f"股票分组数量: {len(STOCK_GROUP_MAPPING)}")
