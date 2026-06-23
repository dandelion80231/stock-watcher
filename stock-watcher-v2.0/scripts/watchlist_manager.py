#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stock Watcher v2.0 - 自选股管理
添加、删除、列表、清空
"""
import sys
import os

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import WATCHLIST_FILE


def get_stock_name_from_api(stock_code: str) -> str:
    """通过东方财富 API 获取股票名称（无需额外依赖）"""
    import json
    import urllib.request
    from config import get_eastmoney_secid

    secid = get_eastmoney_secid(stock_code)
    url = f"https://push2.eastmoney.com/api/qt/stock/get?secid={secid}&fields=f58"
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0',
            'Referer': 'https://quote.eastmoney.com/',
        })
        response = urllib.request.urlopen(req, timeout=5)
        raw = response.read().decode('utf-8')
        result = json.loads(raw)
        if result.get('rc') == 0 and result.get('data'):
            return result['data'].get('f58', stock_code)
    except:
        pass

    # 备选：同花顺
    try:
        url = f"https://stockpage.10jqka.com.cn/{stock_code}/"
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        response = urllib.request.urlopen(req, timeout=5)
        response.encoding = 'utf-8'
        if response.status == 200:
            import re
            text = response.read().decode('utf-8')
            match = re.search(r'<title>(.*?)\(', text)
            if match:
                return match.group(1).strip()
    except:
        pass

    return stock_code


def add_stock(stock_code: str, stock_name: str = None) -> bool:
    """添加股票到自选股列表"""
    # 确保目录存在
    os.makedirs(os.path.dirname(WATCHLIST_FILE), exist_ok=True)

    # 自动获取名称
    if not stock_name:
        stock_name = get_stock_name_from_api(stock_code)

    # 读取现有列表
    existing = _read_watchlist()

    # 检查是否已存在
    if stock_code in existing:
        print(f"股票 {stock_code} 已在自选列表中")
        return False

    # 添加
    existing[stock_code] = stock_name
    _write_watchlist(existing)
    print(f"✅ 已添加 {stock_name}({stock_code}) 到自选列表")
    return True


def remove_stock(stock_code: str) -> bool:
    """从自选股列表删除股票"""
    existing = _read_watchlist()

    if stock_code not in existing:
        print(f"股票 {stock_code} 不在自选列表中")
        return False

    name = existing[stock_code]
    del existing[stock_code]
    _write_watchlist(existing)
    print(f"✅ 已从自选列表删除 {name}({stock_code})")
    return True


def list_stocks():
    """列出所有自选股"""
    existing = _read_watchlist()

    if not existing:
        print("自选股列表为空")
        return

    print("=" * 40)
    print("📋 自选股列表")
    print("=" * 40)
    for i, (code, name) in enumerate(existing.items(), 1):
        print(f"  {i}. {code} - {name}")
    print("=" * 40)
    print(f"共 {len(existing)} 只")


def clear_watchlist():
    """清空自选股列表"""
    _write_watchlist({})
    print("✅ 自选股列表已清空")


def _read_watchlist() -> dict:
    """读取自选股列表为有序字典 {code: name}"""
    result = {}
    if os.path.exists(WATCHLIST_FILE):
        with open(WATCHLIST_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if '|' in line:
                    parts = line.split('|', 1)
                    result[parts[0]] = parts[1] if len(parts) > 1 else parts[0]
    return result


def _write_watchlist(data: dict):
    """写入自选股列表"""
    os.makedirs(os.path.dirname(WATCHLIST_FILE), exist_ok=True)
    with open(WATCHLIST_FILE, 'w', encoding='utf-8') as f:
        for code, name in data.items():
            f.write(f"{code}|{name}\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python add_stock.py <股票代码> [股票名称]")
        print("      python remove_stock.py <股票代码>")
        print("      python list_stocks.py")
        print("      python clear_watchlist.py")
        sys.exit(1)

    cmd = os.path.basename(__file__).replace('.py', '')
    if cmd == 'add_stock':
        code = sys.argv[1]
        name = sys.argv[2] if len(sys.argv) > 2 else None
        add_stock(code, name)
    elif cmd == 'remove_stock':
        remove_stock(sys.argv[1])
    elif cmd == 'list_stocks':
        list_stocks()
    elif cmd == 'clear_watchlist':
        clear_watchlist()
