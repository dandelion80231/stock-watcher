#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stock Watcher v2.0 - 盘中监控与预警
支持三数据源自动切换，价格预警、涨跌幅预警、成交量异常检测
"""
import os
import sys
import json
from datetime import datetime

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import (
    WATCHLIST_FILE, MONITOR_CONFIG_FILE, ALERT_LOG_FILE,
    PORTFOLIO_FILE, DEFAULT_MONITOR_CONFIG, load_json, save_json,
)
from data_source import fetch_stock_data


def load_monitor_config() -> dict:
    """加载监控配置"""
    config = load_json(MONITOR_CONFIG_FILE, DEFAULT_MONITOR_CONFIG.copy())
    # 合并默认值
    for key in DEFAULT_MONITOR_CONFIG:
        if key not in config:
            config[key] = DEFAULT_MONITOR_CONFIG[key]
    return config


def save_monitor_config(config: dict):
    """保存监控配置"""
    save_json(MONITOR_CONFIG_FILE, config)


def set_price_alert(stock_code: str, high: float = None, low: float = None):
    """设置价格预警"""
    config = load_monitor_config()
    if 'price_alerts' not in config:
        config['price_alerts'] = {}

    if stock_code not in config['price_alerts']:
        config['price_alerts'][stock_code] = {}

    if high is not None:
        config['price_alerts'][stock_code]['high'] = high
    if low is not None:
        config['price_alerts'][stock_code]['low'] = low

    save_monitor_config(config)

    parts = []
    if high is not None:
        parts.append(f"目标价 ¥{high}")
    if low is not None:
        parts.append(f"止损价 ¥{low}")
    print(f"✅ 已设置 {stock_code} 预警：{' / '.join(parts)}")


def set_change_threshold(threshold: float):
    """设置涨跌幅预警阈值"""
    config = load_monitor_config()
    config['change_threshold'] = threshold
    save_monitor_config(config)
    print(f"✅ 涨跌幅预警阈值已设置为 {threshold}%")


def check_alerts() -> list:
    """
    检查所有预警条件，返回触发的预警列表
    适合 cron 定时调用
    """
    now = datetime.now()
    weekday = now.weekday()
    current_time = now.strftime("%H:%M")

    # 非交易时间静默退出
    if weekday >= 5:
        return []
    if not ("09:25" <= current_time <= "15:05"):
        return []

    # 读取自选股
    if not os.path.exists(WATCHLIST_FILE):
        return []

    stock_codes = []
    with open(WATCHLIST_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and '|' in line:
                stock_codes.append(line.split('|')[0])

    if not stock_codes:
        return []

    # 获取实时数据
    stock_data = fetch_stock_data(stock_codes)
    if not stock_data:
        return []

    config = load_monitor_config()
    alerts = []

    change_threshold = config.get('change_threshold', 5.0)
    price_alerts = config.get('price_alerts', {})

    for code, data in stock_data.items():
        name = data.get('name', code)
        current = data.get('current', 0)
        prev_close = data.get('prev_close', 0)
        change_pct_num = data.get('change_pct_num', 0)

        # 1. 涨跌幅预警
        if abs(change_pct_num) >= change_threshold:
            direction = "🔴 大涨" if change_pct_num > 0 else "🟢 大跌"
            alerts.append(f"{direction} {name}({code}) 涨跌幅 {change_pct_num:+.2f}%，当前 ¥{current}")

        # 2. 价格预警
        if code in price_alerts:
            pa = price_alerts[code]
            if 'high' in pa and pa['high'] and current >= pa['high']:
                alerts.append(f"🎯 {name}({code}) 达到目标价 ¥{current}（设定 ¥{pa['high']}）")
            if 'low' in pa and pa['low'] and current <= pa['low']:
                alerts.append(f"🛑 {name}({code}) 触及止损价 ¥{current}（设定 ¥{pa['low']}）")

        # 3. 涨跌停预警
        try:
            if prev_close > 0:
                limit_up_price = round(prev_close * 1.1, 2)
                limit_down_price = round(prev_close * 0.9, 2)
                if current >= limit_up_price:
                    alerts.append(f"⛔ {name}({code}) 可能涨停！当前 ¥{current}")
                elif current <= limit_down_price:
                    alerts.append(f"⛔ {name}({code}) 可能跌停！当前 ¥{current}")
        except:
            pass

    # 记录预警日志
    if alerts:
        log = load_json(ALERT_LOG_FILE, [])
        log.append({
            'time': now.strftime('%Y-%m-%d %H:%M:%S'),
            'alerts': alerts,
        })
        # 只保留最近 100 条
        save_json(ALERT_LOG_FILE, log[-100:])

    return alerts


def monitor():
    """主监控函数，供 cron 调用"""
    alerts = check_alerts()
    if alerts:
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print("=" * 60)
        print(f"⚠️ 股票预警提醒 ({now})")
        print("=" * 60)
        for alert in alerts:
            print(f"  {alert}")
        print("=" * 60)


def show_monitor_config():
    """显示当前监控配置"""
    config = load_monitor_config()
    print("=" * 50)
    print("📋 监控配置")
    print("=" * 50)
    print(f"  涨跌幅阈值: {config.get('change_threshold', 5.0)}%")
    print(f"  成交量放大倍数: {config.get('volume_surge_ratio', 2.0)}")
    print(f"  监控间隔: {config.get('check_interval_seconds', 60)} 秒")

    price_alerts = config.get('price_alerts', {})
    if price_alerts:
        print(f"\n  📌 价格预警:")
        for code, pa in price_alerts.items():
            parts = []
            if 'high' in pa:
                parts.append(f"目标价 ¥{pa['high']}")
            if 'low' in pa:
                parts.append(f"止损价 ¥{pa['low']}")
            print(f"    {code}: {' / '.join(parts)}")
    else:
        print(f"\n  📌 暂无价格预警设置")

    print("=" * 50)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        monitor()
        sys.exit(0)

    cmd = sys.argv[1]
    if cmd == 'config':
        show_monitor_config()
    elif cmd == 'alert':
        # 设置预警: python monitor_stocks.py alert 600519 high 35
        if len(sys.argv) >= 5:
            code = sys.argv[2]
            alert_type = sys.argv[3]
            price = float(sys.argv[4])
            if alert_type == 'high':
                set_price_alert(code, high=price)
            elif alert_type == 'low':
                set_price_alert(code, low=price)
        else:
            print("用法: python monitor_stocks.py alert <代码> <high/low> <价格>")
    elif cmd == 'threshold':
        if len(sys.argv) >= 3:
            set_change_threshold(float(sys.argv[2]))
        else:
            print("用法: python monitor_stocks.py threshold <百分比>")
    else:
        monitor()
