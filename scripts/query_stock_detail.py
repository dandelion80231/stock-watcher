#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stock Watcher v2.0 - 股票详情查询
支持东方财富 + 腾讯双数据源，含买卖五档
"""
import sys
import os

try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data_source import fetch_stock_detail


def display_stock_detail(stock_code: str):
    """查询并显示股票完整详情"""
    # 验证代码格式
    if not stock_code.isdigit() or len(stock_code) != 6:
        print("❌ 股票代码格式不正确，应为6位数字（如 600519）")
        return

    print(f"\n🔍 正在查询 {stock_code} 的详细数据...\n")

    data = fetch_stock_detail(stock_code)
    if not data:
        print("❌ 查询失败，请检查股票代码或网络连接")
        return

    source = data.get('source', 'unknown')

    print("=" * 70)
    print(f"  {data.get('name', '')} ({stock_code})")
    print("=" * 70)

    # 行情数据
    print(f"\n【行情数据】")
    print(f"  当前价:   ¥{data['current']}")
    print(f"  昨收:     ¥{data['prev_close']}")
    print(f"  今开:     ¥{data.get('open', 'N/A')}")
    print(f"  最高:     ¥{data.get('high', 'N/A')}")
    print(f"  最低:     ¥{data.get('low', 'N/A')}")
    print(f"  涨跌幅:   {data.get('change_pct', 'N/A')}")
    print(f"  振幅:     {data.get('amplitude', 'N/A')}%")

    # 交易数据
    print(f"\n【交易数据】")
    vol = data.get('volume', 0)
    amt = data.get('amount', 0)
    try:
        vol_display = f"{int(vol)} 手" if vol else 'N/A'
    except:
        vol_display = f"{vol} 手"
    print(f"  成交量:   {vol_display}")
    print(f"  成交额:   {_format_amount(amt)}")
    print(f"  换手率:   {data.get('turnover_rate', 'N/A')}%")

    # 市值数据
    print(f"\n【市值数据】")
    print(f"  总市值:   {_format_market_cap(data.get('total_mv', 0))}")
    print(f"  流通市值: {_format_market_cap(data.get('circ_mv', 0))}")

    # 估值指标
    print(f"\n【估值指标】")
    print(f"  市盈率(动态): {data.get('pe', 'N/A')}")
    print(f"  市净率:       {data.get('pb', 'N/A')}")

    # 涨跌停
    limit_up = data.get('limit_up', 0)
    limit_down = data.get('limit_down', 0)
    if limit_up or limit_down:
        print(f"\n【涨跌停】")
        print(f"  涨停价:   ¥{limit_up}")
        print(f"  跌停价:   ¥{limit_down}")

    # 买卖五档
    print(f"\n【买卖五档】")
    for i in range(1, 6):
        bp = data.get(f'bid{i}_price', 0)
        bv = data.get(f'bid{i}_vol', 0)
        ap = data.get(f'ask{i}_price', 0)
        av = data.get(f'ask{i}_vol', 0)
        print(f"  买{i}: ¥{bp} ({_format_vol(bv)})  |  卖{i}: ¥{ap} ({_format_vol(av)})")

    # 数据源
    print(f"\n  [数据源: {source}]")
    print("=" * 70)


def _format_amount(val) -> str:
    """格式化成交额"""
    try:
        v = float(val)
        if v >= 1e8:
            return f"{v/1e8:.2f} 亿"
        elif v >= 1e4:
            return f"{v/1e4:.2f} 万"
        else:
            return f"{v:.0f} 元"
    except:
        return str(val)


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
        return "N/A"
    except:
        return "N/A"


def _format_vol(val) -> str:
    """格式化手数"""
    try:
        v = int(val)
        return f"{v}手"
    except:
        return f"{val}手"


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python query_stock_detail.py <股票代码>")
        print("示例: python query_stock_detail.py 600519")
        sys.exit(1)

    display_stock_detail(sys.argv[1])
