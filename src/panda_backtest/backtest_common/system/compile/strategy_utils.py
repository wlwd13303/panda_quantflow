# -*- coding: utf-8 -*-
"""
File: strategy_utils.py
Author: peiqi
Date: 2025/5/14
Description: 
"""
import six
import logging

import codecs
from panda_backtest.backtest_common.exception.error_exception import ErrorException
from panda_backtest.backtest_common.exception.strategy_exception_builder import StrategyExceptionBuilder
class FileStrategyLoader(object):

    def __init__(self, strategy_info, local_run):
        self._local_run = local_run
        if local_run:
            self._strategy_file_path = strategy_info
        else:
            self._strategy_file_path = '<string>'
            self.code = strategy_info

    def load(self, scope):
        if self._local_run:
            with codecs.open(self._strategy_file_path, encoding="utf-8") as f:
                source_code = f.read()
            return strategy_compile(source_code, self._strategy_file_path, scope)
        else:
            return strategy_compile(self.code, self._strategy_file_path, scope)

def strategy_compile(source_code, strategy, scope):
    try:
        code = compile(source_code, strategy, 'exec')
        six.exec_(code, scope)
        return scope
    except Exception as e:
        raise ErrorException(StrategyExceptionBuilder.build_strategy_compile_exception_msg(), '00001', None)

