#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stock Watcher v2.0 - 风险提示与操盘建议
基于实时行情数据进行风险评估和简单操盘参考
"""
import sys
import os

try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data_source import fetch_stock_data, fetch_stock_detail


def risk_alert(stock_code: str):
    """风险提示：暴涨/暴跌/高波动/涨跌停预警"""
    data = fetch_stock_data([stock_code])
    if not data or stock_code not in data:
        print(f"❌ 无法获取 {stock_code} 的行情数据")
        return

    d = data[stock_code]
    name = d.get('name', stock_code)
    current = d.get('current', 0)
    prev_close = d.get('prev_close', 0)
    change_pct = d.get('change_pct_num', 0)
    turnover = d.get('turnover_rate', 0)
    source = d.get('source', 'unknown')

    print("=" * 60)
    print(f"⚠️ {name}({stock_code}) 风险提示")
    print("=" * 60)
    print(f"  当前价: ¥{current}  涨跌幅: {d['change_pct']}")

    risks = []

    # 涨跌幅风险
    if change_pct >= 9.5:
        risks.append("⛔ 涨停！注意追高风险")
    elif change_pct >= 5:
        risks.append("🔴 大幅上涨，注意短期回调风险")
    elif change_pct <= -9.5:
        risks.append("⛔ 跌停！注意止损")
    elif change_pct <= -5:
        risks.append("🟢 大幅下跌，关注是否破位")

    # 换手率风险
    try:
        tr = float(turnover)
        if tr > 15:
            risks.append(f"⚠️ 换手率 {tr:.1f}%，极度活跃，注意主力动向")
        elif tr > 8:
            risks.append(f"📊 换手率 {tr:.1f}%，较为活跃")
    except:
        pass

    # 高波动预警
    try:
        detail = fetch_stock_detail(stock_code)
        if detail:
            amplitude = detail.get('amplitude', 0)
            try:
                amp = float(amplitude)
                if amp > 8:
                    risks.append(f"⚠️ 振幅 {amp:.1f}%，剧烈波动")
                elif amp > 5:
                    risks.append(f"📊 振幅 {amp:.1f}%，波动较大")
            except:
                pass

            pe = detail.get('pe', 0)
            try:
                pe_val = float(pe)
                if pe_val > 100:
                    risks.append(f"⚠️ 市盈率 {pe_val:.1f}，估值偏高")
                elif pe_val > 0 and pe_val < 8:
                    risks.append(f"📊 市盈率 {pe_val:.1f}，估值较低（注意是否业绩下滑）")
            except:
                pass
    except:
        pass

    if risks:
        for r in risks:
            print(f"  {r}")
    else:
        print("  ✅ 当前无明显风险信号")

    print(f"\n  [数据源: {source}]")
    print("=" * 60)


def trading_advice(stock_code: str):
    """操盘建议：基于简单规则给出参考"""
    data = fetch_stock_data([stock_code])
    if not data or stock_code not in data:
        print(f"❌ 无法获取 {stock_code} 的行情数据")
        return

    d = data[stock_code]
    name = d.get('name', stock_code)
    current = d.get('current', 0)
    prev_close = d.get('prev_close', 0)
    open_price = d.get('open', 0)
    high = d.get('high', 0)
    low = d.get('low', 0)
    change_pct = d.get('change_pct_num', 0)
    source = d.get('source', 'unknown')

    print("=" * 60)
    print(f"💡 {name}({stock_code}) 操盘建议")
    print("=" * 60)
    print(f"  当前价: ¥{current}  涨跌幅: {d['change_pct']}")

    advices = []

    # 开盘 vs 昨收
    try:
        if float(open_price) > float(prev_close) * 1.02:
            advices.append("📈 高开超过2%，关注是否回补缺口")
        elif float(open_price) < float(prev_close) * 0.98:
            advices.append("📉 低开超过2%，关注是否有支撑")
    except:
        pass

    # 日内走势
    try:
        if float(high) > 0 and float(low) > 0:
            day_range = (float(high) - float(low)) / float(low) * 100
            if day_range > 5:
                advices.append(f"📊 日内振幅 {day_range:.1f}%，波动剧烈，注意控制仓位")
    except:
        pass

    # 涨跌判断
    if change_pct > 3:
        advices.append("📈 强势上涨，可关注是否有持续性")
        advices.append("   建议：持仓观望，新高可加仓，回落注意止盈")
    elif change_pct > 0:
        advices.append("📈 小幅上涨，趋势偏多")
        advices.append("   建议：持有为主，关注量能配合")
    elif change_pct > -3:
        advices.append("📉 小幅下跌，趋势偏弱")
        advices.append("   建议：观望为主，等待企稳信号")
    else:
        advices.append("📉 大幅下跌，注意风险")
        advices.append("   建议：减仓或止损，等待反弹信号")

    # 支撑压力位
    try:
        detail = fetch_stock_detail(stock_code)
        if detail:
            limit_up = detail.get('limit_up', 0)
            limit_down = detail.get('limit_down', 0)
            if limit_up:
                advices.append(f"   压力位：¥{limit_up}（涨停价）")
            if limit_down:
                advices.append(f"   支撑位：¥{limit_down}（跌停价）")
    except:
        pass

    for a in advices:
        print(f"  {a}")

    print(f"\n  [数据源: {source}]")
    print("=" * 60)
    print("⚠️ 以上建议仅供参考，不构成投资建议")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: python risk_advice.py <risk|advice> <股票代码>")
        print("示例: python risk_advice.py risk 600519")
        print("      python risk_advice.py advice 600519")
        sys.exit(1)

    action = sys.argv[1]
    code = sys.argv[2]

    if action == 'risk':
        risk_alert(code)
    elif action == 'advice':
        trading_advice(code)
    else:
        print(f"未知操作: {action}")
