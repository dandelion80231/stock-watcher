#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Summarize the performance of all stocks in the watchlist.
支持双数据源：新浪财经API（主） + 腾讯财经API（备用）
切换逻辑：如果新浪API有任何失败，整体切换到腾讯API（不混合数据源）
"""

import os
import sys
import urllib.request
import urllib.parse

# 修复Windows命令行UTF-8编码问题
try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

# Standardized watchlist file path
WATCHLIST_FILE = os.path.expanduser("~/.clawdbot/stock_watcher/watchlist.txt")

# 备用路径（兼容OpenClaw环境）
if not os.path.exists(WATCHLIST_FILE):
    WATCHLIST_FILE = os.path.expanduser("~/.openclaw/stock_watcher/watchlist.txt")

def format_stock_code_for_sina(stock_code):
    """
    将6位股票代码转换为新浪API格式
    沪市（6开头）→ sh + 代码
    深市（0/3开头）→ sz + 代码
    """
    stock_code = stock_code.strip()
    if stock_code.startswith('6'):
        return f'sh{stock_code}'
    else:
        return f'sz{stock_code}'

def format_stock_code_for_tencent(stock_code):
    """
    将6位股票代码转换为腾讯API格式
    沪市（6开头）→ sh + 代码
    深市（0/3开头）→ sz + 代码
    """
    stock_code = stock_code.strip()
    if stock_code.startswith('6'):
        return f'sh{stock_code}'
    else:
        return f'sz{stock_code}'

def fetch_stock_data_from_sina(stock_codes):
    """
    使用新浪财经API批量获取股票实时数据
    返回字典：{stock_code: data_dict}
    """
    if not stock_codes:
        return {}
    
    # 构造API请求
    formatted_codes = [format_stock_code_for_sina(code) for code in stock_codes]
    url = f"http://hq.sinajs.cn/list={','.join(formatted_codes)}"
    
    # 新浪API需要Referer头
    req = urllib.request.Request(url, headers={'Referer': 'https://finance.sina.com.cn'})
    
    try:
        response = urllib.request.urlopen(req, timeout=10)
        data = response.read().decode('gbk')
        
        results = {}
        for line in data.strip().split('\n'):
            if '=' not in line:
                continue
            
            # 解析：var hq_str_sh600519="茅台,1235.000,1240.000,..."
            var_name, values_str = line.split('=', 1)
            stock_code_sina = var_name.split('_')[2].lower()  # sh600519 → 提取代码部分
            values = values_str.strip('"').split(',')
            
            if len(values) < 32 or not values[0]:  # 无数据
                continue
            
            # 映射原始股票代码（去掉sh/sz前缀）
            original_code = stock_code_sina[2:] if stock_code_sina.startswith(('sh', 'sz')) else stock_code_sina
            
            # 解析字段（新浪API返回格式）
            stock_name = values[0]
            open_price = values[1]
            prev_close = values[2]
            current_price = values[3]
            high = values[4]
            low = values[5]
            volume = values[8]   # 成交量（手）
            amount = values[9]   # 成交额（元）
            date = values[30]
            time = values[31]
            
            # 计算涨跌幅
            try:
                current = float(current_price)
                prev = float(prev_close)
                change_pct = ((current - prev) / prev) * 100
                change_symbol = '+' if change_pct >= 0 else ''
                change_str = f'{change_symbol}{change_pct:.2f}%'
            except:
                change_pct = 0
                change_str = 'N/A'
            
            results[original_code] = {
                'name': stock_name,
                'current': current_price,
                'change_pct': change_str,
                'change_pct_num': change_pct,
                'open': open_price,
                'high': high,
                'low': low,
                'prev_close': prev_close,
                'volume': volume,
                'amount': amount,
                'date': date,
                'time': time,
                'source': 'sina'
            }
        
        return results
    
    except Exception as e:
        print(f"新浪API请求失败: {e}", file=sys.stderr)
        return {}

def fetch_stock_data_from_tencent(stock_codes):
    """
    使用腾讯财经API批量获取股票实时数据（备用数据源）
    返回字典：{stock_code: data_dict}
    """
    if not stock_codes:
        return {}
    
    # 构造API请求
    formatted_codes = [format_stock_code_for_tencent(code) for code in stock_codes]
    url = f"http://qt.gtimg.cn/q={','.join(formatted_codes)}"
    
    try:
        response = urllib.request.urlopen(url, timeout=10)
        data = response.read().decode('gbk')
        
        results = {}
        for line in data.strip().split('\n'):
            if '=' not in line:
                continue
            
            # 解析：v_sh600519="1~贵州茅台~600519~1215.00~..."
            var_name, values_str = line.split('=', 1)
            stock_code_tencent = var_name.split('_')[1].lower()  # v_sh600519 → 提取代码部分
            values = values_str.strip('"').split('~')
            
            if len(values) < 40 or not values[1]:  # 无数据
                continue
            
            # 映射原始股票代码（去掉sh/sz前缀）
            original_code = stock_code_tencent[2:] if stock_code_tencent.startswith(('sh', 'sz')) else stock_code_tencent
            
            # 解析字段（腾讯API返回格式，共88个字段）
            stock_name = values[1]
            current_price = values[3]
            prev_close = values[4]
            open_price = values[5]
            volume = values[6]   # 成交量
            high = values[33] if len(values) > 33 else 'N/A'   # 最高价
            low = values[34] if len(values) > 34 else 'N/A'     # 最低价
            change_pct_str = values[32] if len(values) > 32 else '0'  # 涨跌幅（%）
            
            # 计算涨跌幅
            try:
                change_pct = float(change_pct_str)
                change_symbol = '+' if change_pct >= 0 else ''
                change_str = f'{change_symbol}{change_pct:.2f}%'
            except:
                change_pct = 0
                change_str = 'N/A'
            
            # 更新时间（腾讯API不含时间，使用当前时间）
            import datetime
            now = datetime.datetime.now()
            date = now.strftime('%Y-%m-%d')
            time = now.strftime('%H:%M:%S')
            
            results[original_code] = {
                'name': stock_name,
                'current': current_price,
                'change_pct': change_str,
                'change_pct_num': change_pct,
                'open': open_price,
                'high': high,
                'low': low,
                'prev_close': prev_close,
                'volume': volume,
                'amount': 'N/A',  # 腾讯API需要额外字段
                'date': date,
                'time': time,
                'source': 'tencent'
            }
        
        return results
    
    except Exception as e:
        print(f"腾讯API请求失败: {e}", file=sys.stderr)
        return {}

def fetch_stock_data(stock_codes):
    """
    获取股票数据（双数据源切换逻辑）
    
    切换逻辑：
    1. 先尝试新浪API
    2. 如果新浪API完全失败或部分失败（有任何股票没数据），整体切换到腾讯API
    3. 不混合使用两个API的数据
    """
    # 先尝试新浪API
    print("正在从新浪财经获取数据...", file=sys.stderr)
    results = fetch_stock_data_from_sina(stock_codes)
    
    # 判断是否需要切换到腾讯API
    # 条件：新浪API返回空 或 返回的股票数量少于请求的股票数量
    if not results or len(results) < len(stock_codes):
        print("新浪API部分或全部失败，正在整体切换到腾讯财经API...", file=sys.stderr)
        results = fetch_stock_data_from_tencent(stock_codes)
        if results:
            print(f"已切换到腾讯API，成功获取 {len(results)} 只股票数据", file=sys.stderr)
        else:
            print("腾讯API也失败，无法获取行情数据", file=sys.stderr)
    
    return results

def summarize_performance():
    """Summarize performance of all stocks in watchlist."""
    if not os.path.exists(WATCHLIST_FILE):
        print("自选股列表为空，请先添加股票")
        return
    
    with open(WATCHLIST_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 提取所有股票代码
    stock_codes = []
    stock_names = {}
    for line in lines:
        line = line.strip()
        if line and '|' in line:
            parts = line.split('|')
            if len(parts) == 2:
                code, name = parts
                stock_codes.append(code)
                stock_names[code] = name
    
    if not stock_codes:
        print("自选股列表为空，请先添加股票")
        return
    
    # 批量获取数据（双数据源自动切换）
    stock_data = fetch_stock_data(stock_codes)
    
    if not stock_data:
        print("行情数据暂不可用（可能是休市时间或网络问题）")
        return
    
    # 输出结果
    print("=" * 60)
    for code in stock_codes:
        if code in stock_data:
            data = stock_data[code]
            name = stock_names.get(code, data['name'])
            source = data.get('source', 'sina')
            
            print(f"{name} ({code})")
            print(f"  当前价: ¥{data['current']}  ({data['change_pct']})")
            print(f"  今开: ¥{data['open']}  最高: ¥{data['high']}  最低: ¥{data['low']}")
            print(f"  更新时间: {data['date']} {data['time']}  [数据源: {source}]")
            print("-" * 60)
        else:
            print(f"{stock_names.get(code, code)} ({code}) - 数据暂不可用")
            print("-" * 60)

if __name__ == "__main__":
    summarize_performance()
