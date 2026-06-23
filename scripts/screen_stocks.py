#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
按用户选股标准筛选 A股主板标的
用法: python3 screen_stocks.py
"""
import sys, os, json, subprocess, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

WESTOCK = '/home/node/.openclaw/workspace-agent-831becbb/skills/westock-data/scripts/index.js'

# 主板代码判断
def is_main_board(code):
    if code.startswith('sh'):
        return any(code.startswith('sh'+p) for p in ['600','601','603','605'])
    if code.startswith('sz'):
        return any(code.startswith('sz'+p) for p in ['000','001','002','003'])
    return False

def has_st(name):
    return 'ST' in name

# 调用 westock-data CLI
def run_westock(args):
    try:
        r = subprocess.run(['node', WESTOCK] + args, capture_output=True, text=True, timeout=20)
        return r.stdout
    except:
        return ''

# 解析 markdown 表格为 list[dict]
def parse_md_table(md_text, code_field='code'):
    lines = [l for l in md_text.strip().split('\n') if l.startswith('|')]
    if len(lines) < 2:
        return []
    # 表头：按 | 分割，去掉首尾空字符串，strip 每个字段
    headers = [h.strip() for h in lines[0].split('|') if h.strip()]
    rows = []
    for l in lines[2:]:
        # 去掉首尾的 | 再 split
        content = l.strip()
        if content.startswith('|'):
            content = content[1:]
        if content.endswith('|'):
            content = content[:-1]
        vals = [v.strip() for v in content.split('|')]
        # 补齐或截断
        if len(vals) < len(headers):
            vals += [''] * (len(headers) - len(vals))
        rows.append(dict(zip(headers, vals[:len(headers)])))
    return rows

# 1. 从主线板块提取主板标的
def get_candidates_from_sectors():
    # 电子 pt01801080, 通信 pt01801770, 建筑材料 pt01801710
    SECTORS = ['sw1_pt01801080', 'sw1_pt01801770', 'sw1_pt01801710']
    SECTOR_NAMES = {'sw1_pt01801080':'电子', 'sw1_pt01801770':'通信', 'sw1_pt01801710':'建筑材料'}
    candidates = []
    for sec in SECTORS:
        out = run_westock(['sector', sec])
        rows = parse_md_table(out)
        for r in rows:
            code = r.get('code','')
            name = r.get('name','')
            if is_main_board(code) and not has_st(name):
                candidates.append({'code':code, 'name':name, 'sector':SECTOR_NAMES.get(sec,'')})
        print(f"  板块 {SECTOR_NAMES.get(sec,'')} 主板标的数量: {len([c for c in candidates if c['sector']==SECTOR_NAMES.get(sec,'')])}")
    return candidates

# 2. 批量查实时行情，过滤5日涨幅≤20%
def filter_by_price(candidates):
    filtered = []
    batch = 30
    for i in range(0, len(candidates), batch):
        chunk = candidates[i:i+batch]
        codes = [c['code'] for c in chunk]
        out = run_westock(['quote'] + codes)
        rows = parse_md_table(out, 'code')
        row_map = {r.get('code',''): r for r in rows}
        for c in chunk:
            code = c['code']
            r = row_map.get(code)
            if not r:
                continue
            # 找5日涨幅字段
            chg5 = None
            for k,v in r.items():
                if '5' in k and ('涨' in k or 'chg' in k.lower()):
                    try:
                        chg5 = float(v)
                        break
                    except:
                        pass
            # 如果没找到，用涨跌幅估算（跳过）
            if chg5 is None:
                # 用 quote 输出里的字段
                try:
                    chg5 = float(r.get('涨跌幅', r.get('5日涨幅','0')).replace('%',''))
                except:
                    chg5 = 0
            c['chg_5d'] = chg5
            if chg5 <= 20:
                filtered.append(c)
        print(f"  行情过滤进度: {min(i+batch, len(candidates))}/{len(candidates)}")
    return filtered

# 3. 主力5日净流入筛选（≥1亿）
def filter_by_fund_flow(candidates):
    filtered = []
    for c in candidates:
        code = c['code']
        out = run_westock(['asfund', code])
        rows = parse_md_table(out)
        if not rows:
            continue
        r = rows[0]
        try:
            main5d = float(r.get('MainNetFlow5D', '0'))
        except:
            main5d = 0
        c['main_net_5d'] = main5d
        if main5d >= 1e8:  # ≥1亿
            filtered.append(c)
        print(f"  {c['name']}({code}) 主力5日净流入: {main5d/1e8:.1f}亿")
    return filtered

# 4. MACD 金叉 / 红柱放大
def filter_by_macd(candidates):
    filtered = []
    for c in candidates:
        code = c['code']
        out = run_westock(['technical', code, '--group', 'macd'])
        rows = parse_md_table(out)
        if not rows:
            continue
        r = rows[0]
        signal = r.get('MACD金叉死叉','')
        hist = r.get('MACD柱','')
        # 判断金叉或红柱放大
        is_golden = '金叉' in signal
        try:
            hist_val = float(hist)
            prev_hist = float(r.get('前一日MACD柱','0'))
            hist_rising = hist_val > 0 and hist_val > prev_hist
        except:
            hist_rising = False
        if is_golden or hist_rising:
            c['macd_signal'] = signal
            c['macd_hist'] = hist
            filtered.append(c)
        print(f"  {c['name']}({code}) MACD: {signal}, 柱:{hist}")
    return filtered

if __name__ == '__main__':
    print("=== 第一步：从主线板块提取主板标的 ===")
    candidates = get_candidates_from_sectors()
    print(f"主板标的总计: {len(candidates)} 只\n")

    print("=== 第二步：过滤5日涨幅≤20% ===")
    candidates = filter_by_price(candidates)
    print(f"剩余: {len(candidates)} 只\n")

    print("=== 第三步：主力5日净流入≥1亿 ===")
    candidates = filter_by_fund_flow(candidates)
    print(f"剩余: {len(candidates)} 只\n")

    print("=== 第四步：MACD金叉/红柱放大 ===")
    candidates = filter_by_macd(candidates)
    print(f"\n=== 最终筛选结果: {len(candidates)} 只 ===")
    for c in candidates:
        print(f"  {c['name']}({c['code']}) [{c['sector']}] 5日涨:{c.get('chg_5d',0):.1f}% 主力5日净流入:{c.get('main_net_5d',0)/1e8:.1f}亿 MACD:{c.get('macd_signal','')}")
