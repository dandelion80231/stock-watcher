# -*- coding: utf-8 -*-
"""
收盘总结工具 - v3.0 适配版
15:00 后生成当日自选股收盘总结

用法:
  python close_summary.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from monitor import AlertEngine
from config import load_watchlist


def generate_close_summary():
    """生成收盘总结"""
    engine = AlertEngine()
    watchlist = load_watchlist()

    if not watchlist:
        print("自选股列表为空")
        return

    summary = engine.generate_daily_summary(watchlist, include_specials=['XAUUSD'])
    print(summary)
    return summary


if __name__ == '__main__':
    generate_close_summary()
