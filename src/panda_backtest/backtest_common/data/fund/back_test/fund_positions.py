#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time   : 18-3-16 下午3:17
# @Author : wlb
# @File   : fund_positions.py
# @desc   :
from panda_backtest.backtest_common.data.fund.back_test.fund_positions_item import FundPositionsItems
import logging

class FundPositions(object):

    def __init__(self, strategy_context, account):
        self.strategy_context = strategy_context
        self.account = account

    def __getitem__(self, key):

        position_dict = self.strategy_context.all_trade_reverse_result.get_fund_reverse_result(
            self.account).xb_back_test_position_dict

        return FundPositionsItems(key, position_dict, self.strategy_context, self.account)

    def items(self):

        position_dict = self.strategy_context.all_trade_reverse_result.get_fund_reverse_result(
            self.account).dailyResult.xb_back_test_position_dict
        all_pos_dict = dict()

        for key in self.keys():
            all_pos_dict[key] = FundPositionsItems(key, position_dict, self.strategy_context, self.account)

        return all_pos_dict.items()

    def keys(self):

        position_dict = self.strategy_context.all_trade_reverse_result.get_fund_reverse_result(
            self.account).xb_back_test_position_dict

        keys = list()
        for key, item in position_dict.items():
            if item.position > 0:
                keys.append(key)
        return keys

    def values(self):

        position_dict = self.strategy_context.all_trade_reverse_result.get_fund_reverse_result(
            self.account).dailyResult.xb_back_test_position_dict

        all_pos_dict = dict()

        for key in self.keys():
            all_pos_dict[key] = FundPositionsItems(key, position_dict, self.strategy_context, self.account)

        return all_pos_dict.values()

    def __str__(self):
        list = []
        for key in self.keys():
            list.append(key)
        return str(list)
