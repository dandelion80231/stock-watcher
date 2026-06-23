#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stock Watcher v2.0 - 每日收盘报告
市场概览 + 自选股涨跌统计 + 最佳/最差表现
"""
import sys
import os
from datetime import datetime

try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import WATCHLIST_FILE, PORTFOLIO_FILE, load_json
from data_source import fetch_stock_data


def daily_report():
    """生成每日收盘报告"""
    now = datetime.now()

    # 读取自选股
    stock_codes = []
    stock_names = {}
    if os.path.exists(WATCHLIST_FILE):
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
        print("自选股列表为空，无法生成报告")
        return

    # 获取数据
    stock_data = fetch_stock_data(stock_codes)
    if not stock_data:
        print("⚠️ 行情数据暂不可用，无法生成报告")
        return

    # 统计
    up_list = []
    down_list = []
    flat_list = []

    for code in stock_codes:
        if code not in stock_data:
            continue
        d = stock_data[code]
        name = stock_names.get(code, d.get('name', code))
        change = d.get('change_pct_num', 0)
        item = (code, name, d['current'], change, d.get('turnover_rate', 0))

        if change > 0:
            up_list.append(item)
        elif change < 0:
            down_list.append(item)
        else:
            flat_list.append(item)

    # 输出报告
    print("=" * 70)
    print(f"📰 每日收盘报告  {now.strftime('%Y-%m-%d')}")
    print("=" * 70)

    # 市场概览
    total = len(up_list) + len(down_list) + len(flat_list)
    print(f"\n📊 市场概览（自选股）")
    print(f"  涨: {len(up_list)}  跌: {len(down_list)}  平: {len(flat_list)}  合计: {total}")

    # 涨幅前5
    if up_list:
        up_list.sort(key=lambda x: x[3], reverse=True)
        print(f"\n🔴 涨幅前 {min(5, len(up_list))}:")
        for i, (code, name, price, chg, tr) in enumerate(up_list[:5], 1):
            print(f"  {i}. {name}({code}) ¥{price}  {chg:+.2f}%")

    # 跌幅前5
    if down_list:
        down_list.sort(key=lambda x: x[3])
        print(f"\n🟢 跌幅前 {min(5, len(down_list))}:")
        for i, (code, name, price, chg, tr) in enumerate(down_list[:5], 1):
            print(f"  {i}. {name}({code}) ¥{price}  {chg:+.2f}%")

    # 全部股票
    print(f"\n📋 全部自选股详情:")
    print("-" * 70)
    all_stocks = sorted(
        up_list + down_list + flat_list,
        key=lambda x: x[3],
        reverse=True
    )
    for code, name, price, chg, tr in all_stocks:
        marker = "🔴" if chg > 0 else ("🟢" if chg < 0 else "⚪")
        try:
            tr_str = f"{float(tr):.2f}%" if tr else ""
        except:
            tr_str = ""
        print(f"  {marker} {name}({code}) ¥{price}  {chg:+.2f}%  换手:{tr_str}")

    # 持仓报告（如果有持仓数据）
    portfolio = load_json(PORTFOLIO_FILE, {})
    if portfolio:
        print(f"\n💼 持仓盈亏:")
        print("-" * 70)
        total_profit = 0
        total_cost = 0
        for code, pos in portfolio.items():
            cost = pos.get('cost', 0)
            qty = pos.get('quantity', 0)
            name = pos.get('name', code)
            if code in stock_data:
                current = stock_data[code].get('current', 0)
                try:
                    profit = (float(current) - float(cost)) * int(qty)
                    profit_pct = (float(current) - float(cost)) / float(cost) * 100 if float(cost) else 0
                    total_profit += profit
                    total_cost += float(cost) * int(qty)
                    marker = "🔴" if profit >= 0 else "🟢"
                    print(f"  {marker} {name}({code}) 成本¥{cost} 现价¥{current} 盈亏{profit:+.0f}元 ({profit_pct:+.2f}%)")
                except:
                    pass

        if total_cost > 0:
            total_pct = total_profit / total_cost * 100
            marker = "🔴" if total_profit >= 0 else "🟢"
            print(f"\n  {marker} 总盈亏: {total_profit:+,.0f}元 ({total_pct:+.2f}%)")

    print("\n" + "=" * 70)


def set_portfolio(stock_code: str, cost: float, quantity: int, name: str = None):
    """设置持仓"""
    portfolio = load_json(PORTFOLIO_FILE, {})
    portfolio[stock_code] = {
        'cost': cost,
        'quantity': quantity,
        'name': name or stock_code,
    }
    from config import save_json
    save_json(PORTFOLIO_FILE, portfolio)
    print(f"✅ 已设置持仓: {name or stock_code}({stock_code}) 成本¥{cost} 数量{quantity}")


def show_portfolio():
    """显示持仓"""
    portfolio = load_json(PORTFOLIO_FILE, {})
    if not portfolio:
        print("暂无持仓记录")
        return

    print("=" * 50)
    print("💼 持仓列表")
    print("=" * 50)
    for code, pos in portfolio.items():
        print(f"  {pos.get('name', code)}({code}) 成本¥{pos['cost']} 数量{pos['quantity']}")
    print("=" * 50)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        daily_report()
        sys.exit(0)

    cmd = sys.argv[1]
    if cmd == 'portfolio':
        if len(sys.argv) >= 5:
            set_portfolio(sys.argv[2], float(sys.argv[3]), int(sys.argv[4]),
                         sys.argv[5] if len(sys.argv) > 5 else None)
        else:
            show_portfolio()
    else:
        daily_report()
