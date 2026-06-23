#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stock Watcher v2.0 - 自选股管理命令
支持自然语言指令: "添加600519" "删除茅台" "查看自选股"
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import io
if not isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import re
from config import load_watchlist, save_watchlist, DATA_DIR
from data_source import DataSource


def add_stock(code: str, name: str = '') -> str:
    """添加股票到自选股"""
    watchlist = load_watchlist()
    
    # 检查是否已存在
    for s in watchlist:
        if s['code'] == code:
            return f"⚠️ {code} ({s['name']}) 已在自选股中"
    
    # 获取实时名称
    if not name:
        ds = DataSource()
        data = ds.fetch_realtime([code])
        if code in data:
            name = data[code].get('name', '')
    
    watchlist.append({"code": code, "name": name})
    save_watchlist(watchlist)
    return f"✅ 已添加 {code} ({name}) 到自选股"


def remove_stock(code: str) -> str:
    """从自选股删除股票"""
    watchlist = load_watchlist()
    new_list = [s for s in watchlist if s['code'] != code]
    
    if len(new_list) == len(watchlist):
        # 也尝试用名称匹配
        new_list = [s for s in watchlist if s['name'] != code and code not in s['name']]
    
    removed = len(watchlist) - len(new_list)
    if removed > 0:
        save_watchlist(new_list)
        return f"✅ 已删除 {code} (共移除{removed}只)"
    else:
        return f"⚠️ {code} 不在自选股中"


def list_stocks() -> str:
    """列出所有自选股"""
    watchlist = load_watchlist()
    if not watchlist:
        return "📋 自选股列表为空，请先添加股票"
    
    ds = DataSource()
    codes = [s['code'] for s in watchlist]
    data = ds.fetch_realtime(codes, include_specials=['XAUUSD', 'hf_XAU'])
    
    lines = ["📋 自选股列表:"]
    for s in watchlist:
        code = s['code']
        name = s.get('name', '')
        if code in data:
            d = data[code]
            # fundgz 数据源兼容
            if d.get('source') == 'eastmoney_fundgz':
                change_pct = d.get('change_pct', 0)
                color = '🔴' if change_pct > 0 else '🟢' if change_pct < 0 else '⚪'
                unit = d.get('unit', '元')
                lines.append(f"  {color} {d.get('name', name)} ({code}): {d.get('price', 0):.4f} {unit} ({change_pct:+.2f}%)")
            else:
                price = d.get('price', 0)
                prev_close = d.get('prev_close', 0)
                change_pct = (price - prev_close) / prev_close * 100 if prev_close > 0 else 0
                color = '🔴' if change_pct > 0 else '🟢' if change_pct < 0 else '⚪'
                unit = d.get('unit', '元')
                lines.append(f"  {color} {d.get('name', name)} ({code}): {price:.4f} {unit} ({change_pct:+.2f}%)")
        else:
            lines.append(f"  ⚪ {name} ({code}): 暂无数据")
    
    return '\n'.join(lines)


def clear_watchlist() -> str:
    """清空自选股"""
    save_watchlist([])
    return "✅ 已清空自选股列表"


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python manage.py [add|remove|list|clear] [code]")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == 'add':
        if len(sys.argv) < 3:
            print("请提供股票代码")
            sys.exit(1)
        print(add_stock(sys.argv[2]))
    elif cmd == 'remove':
        if len(sys.argv) < 3:
            print("请提供股票代码或名称")
            sys.exit(1)
        print(remove_stock(sys.argv[2]))
    elif cmd == 'list':
        print(list_stocks())
    elif cmd == 'clear':
        print(clear_watchlist())
    else:
        print(f"未知命令: {cmd}")
