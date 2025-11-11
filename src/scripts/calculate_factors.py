#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
因子计算脚本

批量计算指定日期范围的因子数据

使用方法：
    # 计算所有因子
    python scripts/calculate_factors.py --start-date 20200101 --end-date 20250110
    
    # 计算指定因子
    python scripts/calculate_factors.py --factor resistance_factor --start-date 20240101 --end-date 20250110
    
    # 计算指定股票
    python scripts/calculate_factors.py --factor breakthrough_factor --stocks 600519.SH,000858.SZ
"""

import sys
import os
import argparse
from datetime import datetime

# 添加项目路径到sys.path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, 'src'))

from panda_backtest.factor.factor_manager import FactorManager
from panda_backtest.system.panda_log import SRLogger


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='因子计算脚本')
    
    parser.add_argument(
        '--factor',
        type=str,
        default=None,
        help='因子ID（不指定则计算所有因子）'
    )
    
    parser.add_argument(
        '--start-date',
        type=str,
        default='20200101',
        help='开始日期（YYYYMMDD格式，默认：20200101）'
    )
    
    parser.add_argument(
        '--end-date',
        type=str,
        default=datetime.now().strftime('%Y%m%d'),
        help='结束日期（YYYYMMDD格式，默认：今天）'
    )
    
    parser.add_argument(
        '--stocks',
        type=str,
        default=None,
        help='股票代码列表（逗号分隔，不指定则计算全市场）'
    )
    
    return parser.parse_args()


def calculate_single_factor(manager, factor_id, start_date, end_date, stock_list=None):
    """计算单个因子"""
    SRLogger.info(f"\n{'='*70}")
    SRLogger.info(f"开始计算因子: {factor_id}")
    SRLogger.info(f"日期范围: {start_date} ~ {end_date}")
    if stock_list:
        SRLogger.info(f"股票列表: {stock_list}")
    else:
        SRLogger.info(f"股票范围: 全市场")
    SRLogger.info(f"{'='*70}\n")
    
    result = manager.calculate_factor(
        factor_id=factor_id,
        start_date=start_date,
        end_date=end_date,
        stock_list=stock_list
    )
    
    if result.get('success'):
        SRLogger.info(f"\n✅ 因子计算成功: {factor_id}")
        SRLogger.info(f"  - 处理股票数: {result.get('total_stocks', 0)}")
        SRLogger.info(f"  - 成功记录数: {result.get('success_records', 0)}")
        SRLogger.info(f"  - 失败记录数: {result.get('failed_records', 0)}")
        SRLogger.info(f"  - 耗时: {result.get('duration', 0):.2f}秒\n")
    else:
        SRLogger.error(f"\n❌ 因子计算失败: {factor_id}")
        SRLogger.error(f"  - 错误信息: {result.get('message', 'Unknown error')}\n")
    
    return result.get('success', False)


def main():
    """主函数"""
    args = parse_args()
    
    manager = FactorManager()
    
    # 解析股票列表
    stock_list = None
    if args.stocks:
        stock_list = [s.strip() for s in args.stocks.split(',')]
    
    # 获取要计算的因子列表
    if args.factor:
        # 计算指定因子
        factors_to_calculate = [args.factor]
    else:
        # 计算所有因子
        all_factors = manager.get_factor_metadata()
        factors_to_calculate = [f['factor_id'] for f in all_factors]
    
    SRLogger.info("\n" + "="*70)
    SRLogger.info("因子计算任务")
    SRLogger.info("="*70)
    SRLogger.info(f"待计算因子: {', '.join(factors_to_calculate)}")
    SRLogger.info(f"日期范围: {args.start_date} ~ {args.end_date}")
    SRLogger.info("="*70 + "\n")
    
    # 批量计算
    success_count = 0
    failed_count = 0
    total_duration = 0
    
    start_time = datetime.now()
    
    for factor_id in factors_to_calculate:
        success = calculate_single_factor(
            manager, 
            factor_id, 
            args.start_date, 
            args.end_date, 
            stock_list
        )
        
        if success:
            success_count += 1
        else:
            failed_count += 1
    
    end_time = datetime.now()
    total_duration = (end_time - start_time).total_seconds()
    
    # 输出汇总
    SRLogger.info("\n" + "="*70)
    SRLogger.info("计算任务完成")
    SRLogger.info("="*70)
    SRLogger.info(f"总计因子数: {len(factors_to_calculate)}")
    SRLogger.info(f"成功: {success_count}")
    SRLogger.info(f"失败: {failed_count}")
    SRLogger.info(f"总耗时: {total_duration:.2f}秒")
    SRLogger.info("="*70 + "\n")
    
    # 显示因子状态
    SRLogger.info("当前因子状态：")
    all_factors = manager.get_factor_metadata()
    for factor in all_factors:
        status_icon = "✅" if factor['status'] == 'active' else "⚠️"
        coverage = ""
        if factor['coverage_start_date'] and factor['coverage_end_date']:
            coverage = f" ({factor['coverage_start_date']} ~ {factor['coverage_end_date']})"
        SRLogger.info(f"  {status_icon} [{factor['factor_id']}] {factor['factor_name']} - {factor['status']}{coverage}")
    
    return 0 if failed_count == 0 else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        SRLogger.error(f"执行失败: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

