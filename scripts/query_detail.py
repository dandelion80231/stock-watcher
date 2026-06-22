#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stock Watcher v2.0 - 股票详情查询
88字段完整数据 + 技术分析 + 操盘建议
"""
import sys
import io
if not isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from config import load_watchlist
from data_source import DataSource
from technical_analysis import TechnicalAnalyzer


def query_detail(code: str) -> str:
    """查询单只股票完整详情"""
    ds = DataSource()
    ta = TechnicalAnalyzer()
    
    # 获取实时行情
    data_map = ds.fetch_realtime([code])
    if code not in data_map:
        # 尝试特殊品种
        data_map = ds.fetch_realtime([], include_specials=[code])
    
    if code not in data_map:
        return f"⚠️ 无法获取 {code} 的行情数据"
    
    data = data_map[code]
    price = data.get('price', 0)
    prev_close = data.get('prev_close', 0)
    change_pct = (price - prev_close) / prev_close * 100 if prev_close > 0 else 0
    name = data.get('name', code)
    unit = data.get('unit', '元')
    
    color = '🔴' if change_pct > 0 else '🟢' if change_pct < 0 else '⚪'
    
    lines = []
    lines.append('=' * 60)
    lines.append(f'{color} 股票详情: {name} ({code})')
    lines.append('=' * 60)
    
    # === 行情数据 ===
    lines.append('\n【行情数据】')
    lines.append(f'  当前价: {price:.4f} {unit} ({change_pct:+.2f}%)')
    lines.append(f'  昨收: {data.get("prev_close", 0):.4f}')
    lines.append(f'  今开: {data.get("open", 0):.4f}')
    lines.append(f'  最高: {data.get("high", 0):.4f}')
    lines.append(f'  最低: {data.get("low", 0):.4f}')
    
    # === 交易数据 ===
    lines.append('\n【交易数据】')
    vol = data.get('volume', 0)
    amt = data.get('amount', 0)
    lines.append(f'  成交量: {vol} 手')
    lines.append(f'  成交额: {amt:.2f} 万元')
    
    # === 买卖五档 ===
    if data.get('source') == 'tencent':
        lines.append('\n【买卖五档 (腾讯数据源)】')
        for i in range(1, 6):
            bid_key = f'bid{i}_price'
            bid_vol = f'bid{i}_vol'
            ask_key = f'ask{i}_price'
            ask_vol = f'ask{i}_vol'
            if data.get(bid_key):
                lines.append(f'  买{i}: ¥{data.get(bid_key, 0):.3f} ({data.get(bid_vol, 0)}手)')
            if data.get(ask_key):
                lines.append(f'  卖{i}: ¥{data.get(ask_key, 0):.3f} ({data.get(ask_vol, 0)}手)')
    
    # === 技术分析 ===
    stock_type = ds.identify_stock_type(code)
    if stock_type != 'gold':
        lines.append('\n【技术分析】')
        klines = ds.fetch_kline(code, 60)
        if klines and len(klines) >= 20:
            result = ta.analyze(klines)
            
            # MA
            ma = result.get('ma', {})
            lines.append(f'  MA5: {ma.get("MA5", "N/A"):.2f}')
            lines.append(f'  MA10: {ma.get("MA10", "N/A"):.2f}')
            lines.append(f'  MA20: {ma.get("MA20", "N/A"):.2f}')
            lines.append(f'  排列: {ma.get("arrangement", "N/A")}')
            lines.append(f'  金叉: {ma.get("golden_cross", False)} 死叉: {ma.get("death_cross", False)}')
            
            # RSI
            rsi = result.get('rsi', {})
            lines.append(f'  RSI: {rsi.get("value", "N/A")} {rsi.get("signal", "")}')
            
            # MACD
            macd = result.get('macd', {})
            lines.append(f'  MACD: {macd.get("macd", "N/A")} {macd.get("signal", "")}')
            
            # BOLL
            boll = result.get('boll', {})
            lines.append(f'  布林: 上{boll.get("upper", "N/A")} 中{boll.get("middle", "N/A")} 下{boll.get("lower", "N/A")}')
            lines.append(f'  位置: {boll.get("position", "N/A")}')
            
            # 成交量
            vol_ratio = result.get('volume_ratio', {})
            lines.append(f'  量比: {vol_ratio.get("ratio", "N/A")} {vol_ratio.get("signal", "")}')
            
            # 趋势
            trend = result.get('trend', {})
            lines.append(f'  趋势: {trend.get("signal", "")} (5日变动{trend.get("5d_change_pct", "N/A")}%)')
            
            # 综合评分
            score = result.get('score', {})
            lines.append(f'\n  🎯 综合评分: {score.get("value", 0)} {score.get("level", "")}')
            lines.append(f'  💡 建议: {result.get("suggestion", "")}')
        else:
            lines.append('  K线数据不足，无法进行技术分析')
    
    # === 更新时间 ===
    lines.append(f'\n【更新时间】')
    lines.append(f'  {data.get("date", "")} {data.get("time", "")}')
    lines.append(f'  数据源: {data.get("source", "")}')
    lines.append('=' * 60)
    
    return '\n'.join(lines)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python query_detail.py [股票代码]")
        sys.exit(1)
    print(query_detail(sys.argv[1]))
