#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stock Watcher v2.0 - 行情摘要
批量查看自选股实时行情，三数据源自动切换
"""
import sys
import os

try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import WATCHLIST_FILE
from data_source import fetch_stock_data


def summarize_performance():
    """显示自选股行情摘要"""
    # 读取自选股
    if not os.path.exists(WATCHLIST_FILE):
        print("自选股列表为空，请先添加股票（如：添加自选 600519）")
        return

    stock_codes = []
    stock_names = {}
    with open(WATCHLIST_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and '|' in line:
                parts = line.split('|', 1)
                code = parts[0]
                name = parts[1] if len(parts) > 1 else code
                stock_codes.append(code)
                stock_names[code] = name

    if not stock_codes:
        print("自选股列表为空，请先添加股票")
        return

    # 获取实时数据
    stock_data = fetch_stock_data(stock_codes)

    if not stock_data:
        print("⚠️ 行情数据暂不可用（可能是休市时间或网络问题）")
        return

    # 格式化输出
    print("=" * 70)
    print(f"📊 自选股行情摘要  共 {len(stock_codes)} 只")
    print("=" * 70)

    # 涨跌统计
    up_count = 0
    down_count = 0
    flat_count = 0

    for code in stock_codes:
        if code not in stock_data:
            name = stock_names.get(code, code)
            print(f"  {name}({code}) - 数据暂不可用")
            print("-" * 70)
            continue

        data = stock_data[code]
        name = stock_names.get(code, data.get('name', code))
        source = data.get('source', 'unknown')
        change_pct_num = data.get('change_pct_num', 0)

        # 涨跌标记
        if change_pct_num > 0:
            marker = "🔴"  # 涨
            up_count += 1
        elif change_pct_num < 0:
            marker = "🟢"  # 跌
            down_count += 1
        else:
            marker = "⚪"
            flat_count += 1

        # 格式化市值（腾讯/东方财富返回亿元，转为元后交给 _format_market_cap）
        total_mv = data.get('total_mv', 0)
        mv_str = _format_market_cap(total_mv * 1e8) if total_mv else ''

        print(f"  {marker} {name}({code})")
        print(f"     当前价: ¥{data['current']}  {data['change_pct']}")
        print(f"     今开: ¥{data.get('open', 'N/A')}  最高: ¥{data.get('high', 'N/A')}  最低: ¥{data.get('low', 'N/A')}")
        if mv_str:
            print(f"     总市值: {mv_str}  换手率: {data.get('turnover_rate', 'N/A')}%")
        print(f"     [数据源: {source}]")
        print("-" * 70)

    # 汇总统计
    print(f"\n📈 涨 {up_count} 只 | 📉 跌 {down_count} 只 | ➖ 平 {flat_count} 只")


def _format_market_cap(val) -> str:
    """格式化市值"""
    try:
        v = float(val)
        if v >= 1e12:
            return f"{v/1e12:.2f} 万亿"
        elif v >= 1e8:
            return f"{v/1e8:.2f} 亿"
        elif v > 0:
            return f"{v:.0f} 万"
    except:
        pass
    return ""


if __name__ == "__main__":
    summarize_performance()
