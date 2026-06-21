#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票详情查询脚本（通用版）
使用腾讯财经API获取完整的股票数据（88个字段）
支持A股（沪深主板、创业板、科创板、北交所）
"""
import urllib.request
import sys
import os

# 设置输出编码为UTF-8（解决Windows命令行编码问题）
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

def get_market_prefix(stock_code):
    """
    根据股票代码判断市场并返回前缀
    沪市: sh (600/601/603/688/689)
    深市: sz (000/001/002/003/300)
    北交所: bj (430/830/831/832/833/834/835/836/837/838/839/870/871/872/873)
    """
    code = stock_code[:3]
    if code in ['600', '601', '603', '688', '689']:
        return 'sh'
    elif code in ['000', '001', '002', '003', '300']:
        return 'sz'
    elif code in ['430', '830', '831', '832', '833', '834', '835', '836', '837', '838', '839', '870', '871', '872', '873']:
        return 'bj'
    else:
        # 默认返回沪市
        return 'sh'

def fetch_stock_detail(stock_code):
    """从腾讯财经API获取股票详情"""
    market_prefix = get_market_prefix(stock_code)
    formatted_code = f"{market_prefix}{stock_code}"
    url = f"http://qt.gtimg.cn/q={formatted_code}"
    
    try:
        response = urllib.request.urlopen(url, timeout=10)
        data = response.read().decode('gbk')
        
        for line in data.strip().split('\n'):
            if '=' not in line:
                continue
            
            var_name, values_str = line.split('=', 1)
            values = values_str.strip('"').split('~')
            
            if len(values) < 50:
                print(f"错误: 数据字段不足，仅获取到 {len(values)} 个字段")
                return None
            
            return values
        
    except Exception as e:
        print(f"查询失败: {e}")
        return None

def display_stock_detail(values):
    """显示股票详情（格式化输出）"""
    print("=" * 70)
    print(f"股票名称: {values[1]}")
    print(f"股票代码: {values[2]}")
    print("=" * 70)
    
    print(f"\n【行情数据】")
    print(f"  当前价:   ¥{values[3]}")
    print(f"  昨收:     ¥{values[4]}")
    print(f"  今开:     ¥{values[5]}")
    print(f"  最高:     ¥{values[33]}")
    print(f"  最低:     ¥{values[34]}")
    print(f"  涨跌幅:   {values[32]}%")
    print(f"  涨跌额:   ¥{values[31]}")
    
    print(f"\n【交易数据】")
    print(f"  成交量:   {values[6]} 手")
    print(f"  成交额:   {values[37]} 万元")
    print(f"  换手率:   {values[38]}%")
    
    print(f"\n【市值数据】")
    total_market_cap = values[44] if len(values) > 44 else 'N/A'
    circ_market_cap = values[45] if len(values) > 45 else 'N/A'
    total_shares = values[72] if len(values) > 72 else 'N/A'
    
    print(f"  总市值:   {total_market_cap} 亿元")
    print(f"  流通市值: {circ_market_cap} 亿元")
    if total_shares != 'N/A':
        print(f"  总股本:   {total_shares} 股 ({int(total_shares)/100000000:.2f} 亿股)")
    
    print(f"\n【涨跌停数据】")
    print(f"  振幅:     {values[43]}%")
    print(f"  涨停价:   ¥{values[47]}")
    print(f"  跌停价:   ¥{values[48]}")
    
    print(f"\n【技术指标】")
    print(f"  市盈率(动态): {values[39]}")
    print(f"  市净率:      {values[46]}")
    
    # 买卖五档（Level 2数据）
    print(f"\n【买卖五档】")
    print(f"  买一: ¥{values[9]} ({values[10]}手)")
    print(f"  买二: ¥{values[11]} ({values[12]}手)")
    print(f"  买三: ¥{values[13]} ({values[14]}手)")
    print(f"  买四: ¥{values[15]} ({values[16]}手)")
    print(f"  买五: ¥{values[17]} ({values[18]}手)")
    print(f"  卖一: ¥{values[19]} ({values[20]}手)")
    print(f"  卖二: ¥{values[21]} ({values[22]}手)")
    print(f"  卖三: ¥{values[23]} ({values[24]}手)")
    print(f"  卖四: ¥{values[25]} ({values[26]}手)")
    print(f"  卖五: ¥{values[27]} ({values[28]}手)")
    
    # 更新时间
    update_time = values[30] if len(values) > 30 else 'N/A'
    if update_time != 'N/A':
        formatted_time = f"{update_time[:4]}-{update_time[4:6]}-{update_time[6:8]} {update_time[8:10]}:{update_time[10:12]}:{update_time[12:14]}"
        print(f"\n【更新时间】")
        print(f"  {formatted_time}")
    
    print("\n" + "=" * 70)

def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("使用方法: python query_stock_detail.py <股票代码>")
        print("示例: python query_stock_detail.py 600500")
        print("      python query_stock_detail.py 002600")
        print("      python query_stock_detail.py 300750")
        sys.exit(1)
    
    stock_code = sys.argv[1]
    
    # 验证股票代码格式（6位数字）
    if not stock_code.isdigit() or len(stock_code) != 6:
        print(f"错误: 股票代码格式不正确，应为6位数字（如 600500）")
        sys.exit(1)
    
    print(f"\n正在查询股票 {stock_code} 的详细数据...\n")
    
    values = fetch_stock_detail(stock_code)
    
    if values:
        display_stock_detail(values)

if __name__ == "__main__":
    main()
