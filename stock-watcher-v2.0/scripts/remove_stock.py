#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""兼容入口: python remove_stock.py <code>"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from watchlist_manager import remove_stock

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python remove_stock.py <股票代码>")
        sys.exit(1)
    remove_stock(sys.argv[1])
