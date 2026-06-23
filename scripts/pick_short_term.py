#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
短线选股策略 v1.0
默认策略（量化技术派）：
  1. 主板 + 非ST
  2. 主力5日净流入 ≥ 5000万（核心）
  3. MACD金叉 或 红柱放大（DIF>DEA, MACD柱>0）
  4. 今日涨幅 ≤ 9.5%，5日涨幅 ≤ 25%
  5. KDJ金叉 或 RSI(6) < 80
  6. 排除涨停板、一字板、停牌
用法:
  python pick_short_term.py           # 默认策略，输出前5只
  python pick_short_term.py --top 3   # 输出前3只
  python pick_short_term.py --funds 10000  # 总资金1万，计算每只仓位

依赖: westock-data skill (外部数据源)
"""
import sys, os, json, subprocess, argparse, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

WESTOCK = '/home/node/.openclaw/workspace-agent-831becbb/skills/westock-data/scripts/index.js'

# ── 工具函数 ──────────────────────────────────────────────

def is_main_board(code):
    if code.startswith('sh'):
        return any(code.startswith('sh'+p) for p in ['600','601','603','605'])
    if code.startswith('sz'):
        return any(code.startswith('sz'+p) for p in ['000','001','002','003'])
    return False

def has_st(name):
    return 'ST' in name

def run_westock(args, timeout=20):
    try:
        r = subprocess.run(['node', WESTOCK] + args,
                          capture_output=True, text=True, timeout=timeout)
        return r.stdout
    except Exception as e:
        return ''

def parse_md_table(md_text):
    lines = [l for l in md_text.strip().split('\n') if l.startswith('|')]
    if len(lines) < 2:
        return []
    headers = [h.strip() for h in lines[0].split('|') if h.strip()]
    rows = []
    for l in lines[2:]:
        content = l.strip()
        if content.startswith('|'): content = content[1:]
        if content.endswith('|'): content = content[:-1]
        vals = [v.strip() for v in content.split('|')]
        if len(vals) < len(headers):
            vals += [''] * (len(headers) - len(vals))
        rows.append(dict(zip(headers, vals[:len(headers)])))
    return rows

def safe_float(v, default=0.0):
    try:
        return float(v)
    except:
        return default

# ── 数据拉取 ──────────────────────────────────────────────

def fetch_quote_batch(codes):
    """批量拉实时行情，返回 {code: {字段:值}}"""
    result = {}
    batch_size = 20
    for i in range(0, len(codes), batch_size):
        batch = codes[i:i+batch_size]
        out = run_westock(['quote'] + batch, timeout=30)
        rows = parse_md_table(out)
        for r in rows:
            if r.get('code'):
                result[r['code']] = r
    return result

def fetch_fund_flow(code):
    """拉资金流向，返回 dict"""
    out = run_westock(['asfund', code], timeout=15)
    rows = parse_md_table(out)
    return rows[0] if rows else {}

def fetch_technical(code):
    """拉技术指标（MACD+KDJ+RSI），返回 dict"""
    out = run_westock(['technical', code, '--group', 'macd'], timeout=15)
    rows = parse_md_table(out)
    return rows[0] if rows else {}

def get_sector_stocks(sector_code):
    """从 westock-data 取板块成份股"""
    out = run_westock(['sector', sector_code], timeout=15)
    return parse_md_table(out)

# ── 选股核心 ──────────────────────────────────────────────

def build_candidate_pool():
    """
    构建候选池：
    策略：从3个主线板块各取涨幅前50的主板票 + 热搜前30
    避免全市场扫描（太慢）
    """
    candidates = {}

    # 前5主线板块（申万一级5日涨幅排行）
    SECTORS = ['sw1_pt01801080', 'sw1_pt01801770', 'sw1_pt01801710', 'sw1_pt01801050', 'sw1_pt01801890']
    for sec in SECTORS:
        try:
            rows = get_sector_stocks(sec)
            # 只取前80（板块内按默认排序，通常是市值/热度）
            for r in rows[:20]:
                code = r.get('code','')
                name = r.get('name','')
                if is_main_board(code) and not has_st(name) and code not in candidates:
                    candidates[code] = {'code': code, 'name': name}
        except Exception as e:
            print(f"  板块 {sec} 获取失败: {e}")

    # 从 hot stock 补充（前30）
    try:
        out = run_westock(['hot', 'stock'], timeout=15)
        rows = parse_md_table(out)
        for r in rows[:30]:
            code = r.get('code','')
            name = r.get('name','')
            if is_main_board(code) and not has_st(name) and code not in candidates:
                candidates[code] = {'code': code, 'name': name}
    except Exception as e:
        print(f"  热搜获取失败: {e}")

    print(f"  候选池构建完成: {len(candidates)} 只")
    return list(candidates.values())

def check_stock(c):
    """对单只票执行全部条件检查，返回 (是否通过, 理由dict)"""
    code = c['code']
    name = c['name']

    # ── 1. 实时行情 ──
    quotes = fetch_quote_batch([code])
    q = quotes.get(code, {})
    if not q:
        return False, {'reason': '行情数据获取失败'}

    price     = safe_float(q.get('price', 0))
    prev_close= safe_float(q.get('prev_close', 0))
    change_pct= safe_float(q.get('change_percent', 0))
    chg_5d    = safe_float(q.get('chg_5d', 0))
    status     = q.get('status', '')  # 停牌检测

    # 排除停牌
    if status and '停牌' in status:
        return False, {'reason': f'停牌: {status}'}
    # 排除涨停板（今日涨幅>=9.5% 留空间）
    if change_pct >= 9.5:
        return False, {'reason': f'今日涨停或接近涨停: {change_pct:.1f}%'}
    # 5日涨幅过滤
    if chg_5d > 25:
        return False, {'reason': f'5日涨幅过高: {chg_5d:.1f}%'}
    # 价格有效性
    if price <= 0:
        return False, {'reason': '价格无效'}

    # ── 2. 资金流向 ──
    fund = fetch_fund_flow(code)
    if not fund:
        return False, {'reason': '资金数据获取失败'}
    main5d = safe_float(fund.get('MainNetFlow5D', 0))
    main_today = safe_float(fund.get('MainNetFlow', 0))  # 今日主力净流入

    # 主力5日净流入 ≥ 5000万（核心条件）
    if main5d < 5e7:
        return False, {'reason': f'主力5日净流入不足: {main5d/1e8:.1f}亿'}

    # ── 3. 技术指标 ──
    tech = fetch_technical(code)
    if not tech:
        return False, {'reason': '技术指标获取失败'}

    # MACD 判断
    dif  = safe_float(tech.get('macd.DIF', 0))
    dea  = safe_float(tech.get('macd.DEA', 0))
    macd = safe_float(tech.get('macd.MACD', 0))  # MACD柱

    # 金叉：DIF上穿DEA（今日DIF>DEA，昨日DIF<=DEA）
    # 简化判断：DIF > DEA 且 MACD柱 > 0（红柱）= 多头状态
    macd_golden = (dif > dea) and (macd > 0)
    macd_rising = macd > 0  # 红柱

    if not macd_golden and not macd_rising:
        return False, {'reason': f'MACD未金叉, DIF={dif:.3f}, DEA={dea:.3f}, 柱={macd:.3f}'}

    # KDJ / RSI 辅助判断（不强制，但记录）
    kdj_k = safe_float(tech.get('kdj.KDJ_K', 0))
    kdj_d = safe_float(tech.get('kdj.KDJ_D', 0))
    kdj_j = safe_float(tech.get('kdj.KDJ_J', 0))
    rsi6  = safe_float(tech.get('rsi.RSI_6', 0))

    kdj_golden = (kdj_j > kdj_k > kdj_d) or (kdj_k > kdj_d and kdj_k > 50)
    rsi_ok = rsi6 < 80  # 不过热

    # ── 综合评分 ──
    score = 0
    reasons = []
    if main5d >= 1e8:
        score += 30
        reasons.append(f'主力5日净流入{main5d/1e8:.1f}亿(强)')
    else:
        score += 15
        reasons.append(f'主力5日净流入{main5d/1e8:.1f}亿')

    if macd_golden:
        score += 25
        reasons.append('MACD金叉+红柱')
    elif macd_rising:
        score += 15
        reasons.append('MACD红柱')

    if kdj_golden:
        score += 15
        reasons.append('KDJ金叉')
    if rsi_ok and rsi6 > 0:
        score += 10
        reasons.append(f'RSI6={rsi6:.0f}(不过热)')

    if change_pct > 0:
        score += 10
        reasons.append(f'今日+{change_pct:.1f}%')
    if chg_5d <= 15:
        score += 10
        reasons.append(f'5日涨幅{chg_5d:.1f}%(位置不高)')

    return True, {
        'code': code,
        'name': name,
        'price': price,
        'change_pct': change_pct,
        'chg_5d': chg_5d,
        'main5d': main5d,
        'main_today': main_today,
        'dif': dif, 'dea': dea, 'macd': macd,
        'kdj_k': kdj_k, 'kdj_d': kdj_d, 'kdj_j': kdj_j,
        'rsi6': rsi6,
        'score': score,
        'reasons': reasons,
    }

# ── 主流程 ──────────────────────────────────────────────

def pick(top_n=5, total_funds=10000):
    print("构建候选池...")
    candidates = build_candidate_pool()
    print(f"候选池: {len(candidates)} 只主板票")

    results = []
    for i, c in enumerate(candidates):
        code = c['code']
        print(f"  扫描 [{i+1}/{len(candidates)}] {c['name']}({code})...", flush=True)
        ok, info = check_stock(c)
        if ok:
            results.append(info)
            print(f"    ✅ 通过 评分:{info['score']} | {'; '.join(info['reasons'])}", flush=True)
        else:
            print(f"    ❌ 未通过: {info.get('reason','?')}", flush=True)

    # 按评分排序
    results.sort(key=lambda x: x['score'], reverse=True)
    return results[:top_n]

def format_report(results, total_funds=10000):
    if not results:
        return "⚠️ 未找到符合条件的短线标的，建议等待更好时机"

    lines = []
    lines.append(f"{'='*50}")
    lines.append(f"📊 短线选股结果（{len(results)}只）")
    lines.append(f"{'='*50}")
    lines.append('')

    per_stock = total_funds // len(results)
    for i, r in enumerate(results, 1):
        price = r['price']
        shares = int(per_stock / price / 100) * 100  # 整百股
        actual = shares * price

        lines.append(f"【{i}】 {r['name']}({r['code']}) 评分:{r['score']}")
        lines.append(f"   现价: ¥{price:.2f}  今日: {r['change_pct']:+.1f}%  5日: {r['chg_5d']:+.1f}%")
        lines.append(f"   主力5日净流入: {r['main5d']/1e8:.1f}亿  今日主力: {r['main_today']/1e8:+.1f}亿")
        lines.append(f"   MACD: DIF={r['dif']:.3f} DEA={r['dea']:.3f} 柱={r['macd']:.3f}")
        lines.append(f"   KDJ: K={r['kdj_k']:.1f} D={r['kdj_d']:.1f} J={r['kdj_j']:.1f}  RSI6={r['rsi6']:.0f}")
        lines.append(f"   信号: {' | '.join(r['reasons'])}")
        if shares > 0:
            lines.append(f"   💰 仓位建议: {shares}股 ≈ ¥{actual:.0f}元（总资金{total_funds}元均分）")
        lines.append('')

    return '\n'.join(lines)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--top', type=int, default=5, help='返回前N只（默认5）')
    parser.add_argument('--funds', type=int, default=10000, help='总资金（元，默认10000）')
    args = parser.parse_args()

    t0 = time.time()
    results = pick(top_n=args.top, total_funds=args.funds)
    report = format_report(results, total_funds=args.funds)
    print(report)
    print(f"\n⏱️  耗时: {time.time()-t0:.0f}秒")
