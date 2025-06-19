# -*- coding: utf-8 -*-
"""
File: test2.py
Author: peiqi
Date: 2025/5/23
Description: 
"""

import pandas as pd
from scipy.stats import spearmanr

a = [10, 20, 30, 40, 50]
b = [20, 30, 10, 50, 40]

# 方法一：pandas自带
print(pd.Series(a).corr(pd.Series(b), method='spearman'))