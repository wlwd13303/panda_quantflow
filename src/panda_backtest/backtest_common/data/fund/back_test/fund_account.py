#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time   : 18-3-8 下午8:56
# @Author : wlb
# @File   : fund_account.py
# @desc   : 股票账户对象
from panda_backtest.backtest_common.data.fund.back_test.fund_positions import FundPositions
import logging

from panda_backtest.backtest_common.data.fund.base_fund_account import BaseFundAccount

class FundAccount(BaseFundAccount):

    def __init__(self, strategy_context, account):

        self.strategy_context = strategy_context
        self.account = account

    @property
    def cash(self):
        return self.strategy_context.all_trade_reverse_result.get_fund_reverse_result(
            self.account).xb_back_test_account.available_funds

    @property
    def frozen_cash(self):
        return self.strategy_context.all_trade_reverse_result.get_fund_reverse_result(
            self.account).xb_back_test_account.frozen_capital

    @property
    def market_value(self):
        return self.strategy_context.all_trade_reverse_result.get_fund_reverse_result(
            self.account).xb_back_test_account.market_value

    @property
    def total_value(self):
        return self.strategy_context.all_trade_reverse_result.get_fund_reverse_result(
            self.account).xb_back_test_account.total_profit

    @property
    def transaction_cost(self):
        return self.strategy_context.all_trade_reverse_result.get_fund_reverse_result(
            self.account).xb_back_test_account.cost

    @property
    def positions(self):
        return FundPositions(self.strategy_context, self.account)

    @property
    def add_profit(self):
        start_capital = self.strategy_context.run_info.stock_starting_cash
        if self.strategy_context.all_trade_reverse_result.get_fund_reverse_result(
                self.account).start_capital:
            start_capital = self.strategy_context.all_trade_reverse_result.get_fund_reverse_result(
                self.account).start_capital
        return (self.total_value - start_capital) / start_capital

    @property
    def dividend_receivable(self):
        return 0
