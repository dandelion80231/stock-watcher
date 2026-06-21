#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
盘中实时监控脚本 - 检查自选股是否触发预警条件
触发条件时输出提醒信息，由OpenClaw捕获并推送
"""

import os
import sys
import urllib.request
import json
from datetime import datetime

# Add script directory to Python path to import config
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import WATCHLIST_FILE

# 修复Windows命令行UTF-8编码问题
try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

# 配置文件路径
CONFIG_FILE = os.path.join(os.path.dirname(WATCHLIST_FILE), "monitor_config.json")

# 默认监控参数
DEFAULT_CONFIG = {
    "change_threshold": 5.0,  # 涨跌幅阈值（%）
    "price_alerts": {},        # 价格提醒 {股票代码: {"high": 目标价, "low": 止损价}}
    "volume_surge_ratio": 2.0  # 成交量放大倍数（相比5日均量）
}

def load_config():
    """加载监控配置"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # 合并默认配置
                for key in DEFAULT_CONFIG:
                    if key not in config:
                        config[key] = DEFAULT_CONFIG[key]
                return config
        except:
            pass
    
    # 返回默认配置
    return DEFAULT_CONFIG.copy()

def save_config(config):
    """保存监控配置"""
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

def format_stock_code_for_sina(stock_code):
    """转换股票代码为新浪格式"""
    stock_code = stock_code.strip()
    if stock_code.startswith('6'):
        return f'sh{stock_code}'
    else:
        return f'sz{stock_code}'

def fetch_stock_data_from_sina(stock_codes):
    """从新浪API获取股票实时数据"""
    if not stock_codes:
        return {}
    
    formatted_codes = [format_stock_code_for_sina(code) for code in stock_codes]
    url = f"http://hq.sinajs.cn/list={','.join(formatted_codes)}"
    
    req = urllib.request.Request(url, headers={'Referer': 'https://finance.sina.com.cn'})
    
    try:
        response = urllib.request.urlopen(req, timeout=10)
        data = response.read().decode('gbk')
        
        results = {}
        for line in data.strip().split('\n'):
            if '=' not in line:
                continue
            
            var_name, values_str = line.split('=', 1)
            stock_code_sina = var_name.split('_')[2].lower()
            values = values_str.strip('"').split(',')
            
            if len(values) < 32 or not values[0]:
                continue
            
            original_code = stock_code_sina[2:] if stock_code_sina.startswith(('sh', 'sz')) else stock_code_sina
            
            results[original_code] = {
                'name': values[0],
                'open': float(values[1]),
                'prev_close': float(values[2]),
                'current': float(values[3]),
                'high': float(values[4]),
                'low': float(values[5]),
                'volume': int(values[8]),
                'amount': float(values[9]),
                'date': values[30],
                'time': values[31]
            }
        
        return results
    
    except Exception as e:
        print(f"获取数据失败: {e}", file=sys.stderr)
        return {}

def check_alerts(stock_data, config):
    """
    检查是否触发预警条件
    返回触发预警的消息列表
    """
    alerts = []
    
    change_threshold = config.get('change_threshold', 5.0)
    price_alerts = config.get('price_alerts', {})
    
    for code, data in stock_data.items():
        name = data['name']
        current = data['current']
        prev_close = data['prev_close']
        
        # 计算涨跌幅
        if prev_close > 0:
            change_pct = ((current - prev_close) / prev_close) * 100
        else:
            change_pct = 0
        
        # 检查涨跌幅阈值
        if abs(change_pct) >= change_threshold:
            direction = "大涨" if change_pct > 0 else "大跌"
            alert = f"⚠️ {name}({code}) {direction} {change_pct:+.2f}%，当前价 ¥{current}"
            alerts.append(alert)
        
        # 检查价格提醒
        if code in price_alerts:
            alerts_config = price_alerts[code]
            
            if 'high' in alerts_config and current >= alerts_config['high']:
                alert = f"🎯 {name}({code}) 达到目标价 ¥{current}（设定价 ¥{alerts_config['high']}）"
                alerts.append(alert)
            
            if 'low' in alerts_config and current <= alerts_config['low']:
                alert = f"🛑 {name}({code}) 触及止损价 ¥{current}（设定价 ¥{alerts_config['low']}）"
                alerts.append(alert)
    
    return alerts

def main():
    """主函数"""
    # 检查是否在交易时间（周一至周五 09:30-15:00）
    now = datetime.now()
    weekday = now.weekday()  # 0=周一, 6=周日
    
    if weekday >= 5:  # 周末
        # print("今天是周末，休市")
        sys.exit(0)
    
    current_time = now.strftime("%H:%M")
    if not ("09:30" <= current_time <= "15:00"):
        # print(f"当前时间 {current_time} 不在交易时间内")
        sys.exit(0)
    
    # print(f"监控时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 加载配置
    config = load_config()
    
    # 读取自选股列表
    if not os.path.exists(WATCHLIST_FILE):
        # print("自选股列表不存在")
        sys.exit(0)
    
    with open(WATCHLIST_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    stock_codes = []
    for line in lines:
        line = line.strip()
        if line and '|' in line:
            parts = line.split('|')
            if len(parts) == 2:
                stock_codes.append(parts[0])
    
    if not stock_codes:
        # print("自选股列表为空")
        sys.exit(0)
    
    # 获取实时行情
    stock_data = fetch_stock_data_from_sina(stock_codes)
    
    if not stock_data:
        # print("获取行情数据失败")
        sys.exit(1)
    
    # 检查预警条件
    alerts = check_alerts(stock_data, config)
    
    # 输出预警信息
    if alerts:
        print("=" * 60)
        print(f"⚠️ 股票预警提醒 ({now.strftime('%Y-%m-%d %H:%M:%S')})")
        print("=" * 60)
        for alert in alerts:
            print(alert)
        print("=" * 60)
        sys.exit(2)  # 返回非0退出码，表示有预警触发
    else:
        # 无预警，不输出
        sys.exit(0)

if __name__ == "__main__":
    main()
