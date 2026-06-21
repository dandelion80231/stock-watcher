#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""简单测试腾讯API"""
import sys
sys.path.insert(0, '.')
from summarize_performance import fetch_stock_data_from_tencent

print("测试腾讯API...")
results = fetch_stock_data_from_tencent(['600519', '002600'])
print(f"成功获取 {len(results)} 只股票数据")
for code in results:
    data = results[code]
    print(f"{data['name']} ({code}): ¥{data['current']} ({data['change_pct']}) [数据源: {data['source']}]")
