#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""兼容入口: python clear_watchlist.py"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from watchlist_manager import clear_watchlist

if __name__ == "__main__":
    clear_watchlist()
