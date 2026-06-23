#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""兼容入口: python add_stock.py <code> [name]"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from watchlist_manager import add_stock

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python add_stock.py <股票代码> [股票名称]")
        sys.exit(1)
    add_stock(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
