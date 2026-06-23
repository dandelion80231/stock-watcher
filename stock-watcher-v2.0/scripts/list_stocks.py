#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""兼容入口: python list_stocks.py"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from watchlist_manager import list_stocks

if __name__ == "__main__":
    list_stocks()
