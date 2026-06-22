#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stock Watcher v2.0 - 选股策略与深度分析模块

整合自 perrykono-debug/stock-watcher-v2 的两大框架:
1. 段永平价值投资框架 - 基本面分析
2. Serenity供应链瓶颈筛选 - 瓶颈标的识别

加上我们已有的东方财富 emweb 基本面数据接口
"""
import sys
import io
if not isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from data_source import DataSource
from technical_analysis import TechnicalAnalyzer
from datetime import datetime


class DuanYongpingAnalyzer:
    """段永平投资框架分析器 - 基本面分析
    
    核心三问:
    1. 这家公司赚钱吗？ → ROE/净利润增长/毛利率
    2. 生意模式好吗？ → 护城河/竞争格局
    3. 价格合理吗？ → PE/PB历史分位
    
    判断标准:
    ✅ 好公司+好价格 = 买入
    ⚠️ 好公司+贵价格 = 观望
    ❌ 差公司+任何价格 = 回避
    """

    # 评分阈值
    ROE_EXCELLENT = 20   # ROE > 20% 卓越
    ROE_GOOD = 15        # ROE > 15% 优秀
    NET_PROFIT_GROWTH_GOOD = 10  # 净利润增长 > 10%
    GROSS_MARGIN_STRONG = 40     # 毛利率 > 40% 有定价权
    NET_MARGIN_EXCELLENT = 20    # 净利率 > 20% 优秀
    PE_LOW = 15          # PE < 15 低估
    PE_REASONABLE = 25   # PE < 25 合理
    PE_HIGH = 40         # PE < 40 可接受(卓越公司)
    DEBT_RATIO_SAFE = 30 # 负债率 < 30% 安全

    def analyze(self, code: str, ds: DataSource = None) -> dict:
        """执行段永平三问分析"""
        if ds is None:
            ds = DataSource()

        # 获取基本面数据
        financial = ds.fetch_financial(code)
        if not financial:
            return {
                'code': code,
                'error': '基本面数据获取失败',
                'conclusion': '❌ 数据不足，无法分析，建议观望',
                'score': 0,
            }

        # 获取实时价格
        realtime = ds.fetch_realtime([code])
        price_data = realtime.get(code, {})
        current_price = price_data.get('price', 0)

        # ---- 三问评分 ----
        scores = {}
        details = {}

        # 第一问: 这家公司赚钱吗？
        roe = financial.get('roe', 0) or 0
        net_profit_growth = financial.get('net_profit_growth', 0) or 0
        gross_margin = financial.get('gross_margin', 0) or 0
        net_margin = financial.get('net_margin', 0) or 0
        eps = financial.get('eps', 0) or 0

        profitability_score = 0
        if roe >= self.ROE_EXCELLENT:
            profitability_score += 3
            details['roe'] = f'✅ ROE {roe:.1f}% (卓越 > 20%)'
        elif roe >= self.ROE_GOOD:
            profitability_score += 2
            details['roe'] = f'✅ ROE {roe:.1f}% (优秀 > 15%)'
        elif roe > 0:
            profitability_score += 1
            details['roe'] = f'⚠️ ROE {roe:.1f}% (偏低 < 15%)'
        else:
            details['roe'] = f'❌ ROE {roe:.1f}% (亏损)'

        if net_profit_growth >= self.NET_PROFIT_GROWTH_GOOD:
            profitability_score += 2
            details['growth'] = f'✅ 净利润增长 {net_profit_growth:.1f}% (> 10%)'
        elif net_profit_growth > 0:
            profitability_score += 1
            details['growth'] = f'⚠️ 净利润增长 {net_profit_growth:.1f}% (< 10%)'
        else:
            details['growth'] = f'❌ 净利润增长 {net_profit_growth:.1f}% (下滑)'

        if gross_margin >= self.GROSS_MARGIN_STRONG:
            profitability_score += 2
            details['margin'] = f'✅ 毛利率 {gross_margin:.1f}% (有定价权 > 40%)'
        elif gross_margin > 0:
            profitability_score += 1
            details['margin'] = f'⚠️ 毛利率 {gross_margin:.1f}% (偏低 < 40%)'

        scores['profitability'] = profitability_score  # max 7

        # 第二问: 生意模式好吗? (基于已有数据推断)
        debt_ratio = financial.get('asset_liability_ratio', 0) or 0
        cash_ratio = financial.get('cash_ratio', 0) or 0

        business_score = 0
        if debt_ratio < self.DEBT_RATIO_SAFE:
            business_score += 2
            details['debt'] = f'✅ 负债率 {debt_ratio:.1f}% (安全 < 30%)'
        elif debt_ratio < 60:
            business_score += 1
            details['debt'] = f'⚠️ 负债率 {debt_ratio:.1f}% (偏高)'
        else:
            details['debt'] = f'❌ 负债率 {debt_ratio:.1f}% (危险 > 60%)'

        if cash_ratio >= 0.5:
            business_score += 1
            details['cash'] = f'✅ 现金流量比率 {cash_ratio:.2f} (健康)'
        elif cash_ratio > 0:
            details['cash'] = f'⚠️ 现金流量比率 {cash_ratio:.2f} (偏低)'
        
        # 高毛利率=护城河
        if gross_margin >= 60:
            business_score += 2
            details['moat'] = f'✅ 强护城河 (毛利率 {gross_margin:.1f}% > 60%)'
        elif gross_margin >= self.GROSS_MARGIN_STRONG:
            business_score += 1
            details['moat'] = f'⚠️ 中等护城河 (毛利率 {gross_margin:.1f}%)'
        
        scores['business'] = business_score  # max 5

        # 第三问: 价格合理吗?
        pe = financial.get('pe_ttm', 0) or 0
        bps = financial.get('bps', 0) or 0

        valuation_score = 0
        if current_price > 0 and bps > 0:
            pb = current_price / bps
            if pe > 0:
                if pe <= self.PE_LOW:
                    valuation_score += 3
                    details['valuation'] = f'✅ PE(TTM) {pe:.1f} (低估 < 15倍)'
                elif pe <= self.PE_REASONABLE:
                    valuation_score += 2
                    details['valuation'] = f'✅ PE(TTM) {pe:.1f} (合理 15-25倍)'
                elif pe <= self.PE_HIGH:
                    valuation_score += 1
                    details['valuation'] = f'⚠️ PE(TTM) {pe:.1f} (偏高 25-40倍)'
                else:
                    details['valuation'] = f'❌ PE(TTM) {pe:.1f} (昂贵 > 40倍)'
            details['pb'] = f'PB {pb:.2f}'
        else:
            details['valuation'] = '⚠️ 数据不足，无法评估估值'

        scores['valuation'] = valuation_score  # max 3

        # ---- 综合评分 ----
        total_score = scores['profitability'] + scores['business'] + scores['valuation']
        max_score = 7 + 5 + 3  # = 15

        # 判断结论
        name = financial.get('name', code)
        if total_score >= 10:
            conclusion = '✅ 好公司+好价格 → 买入'
            level = 'strong_buy'
        elif total_score >= 7:
            conclusion = '⚠️ 好公司+贵价格 → 观望等回调'
            level = 'watch'
        elif total_score >= 4:
            conclusion = '⚠️ 一般公司 → 谨慎'
            level = 'caution'
        else:
            conclusion = '❌ 差公司 → 回避'
            level = 'avoid'

        # 止损/目标价
        stop_loss = ''
        target_price = ''
        if current_price > 0:
            stop_loss = f'{current_price * 0.92:.2f}'  # -8%
            if level == 'strong_buy':
                target_price = f'{current_price * 1.2:.2f}'  # +20%
            elif level == 'watch':
                target_price = f'{current_price * 1.1:.2f}'  # +10%

        return {
            'code': code,
            'name': name,
            'current_price': current_price,
            'report_date': financial.get('report_date', ''),
            'scores': scores,
            'total_score': total_score,
            'max_score': max_score,
            'details': details,
            'conclusion': conclusion,
            'level': level,
            'stop_loss': stop_loss,
            'target_price': target_price,
            'financial_raw': financial,
        }

    def format_report(self, result: dict) -> str:
        """格式化段永平框架分析报告"""
        if result.get('error'):
            return f"⚠️ {result['code']}: {result['error']}"

        lines = []
        lines.append(f"{'='*50}")
        lines.append(f"📋 段永平框架分析 · {result['name']} ({result['code']})")
        lines.append(f"{'='*50}")
        lines.append(f"💰 当前价格: {result['current_price']:.2f} 元")
        lines.append(f"📅 最新财报: {result['report_date']}")
        lines.append('')

        # 三问评分
        lines.append(f"📊 综合评分: {result['total_score']}/{result['max_score']}")
        lines.append('')

        lines.append("【第一问: 这家公司赚钱吗？】")
        lines.append(f"  评分: {result['scores']['profitability']}/7")
        for key in ['roe', 'growth', 'margin']:
            if key in result['details']:
                lines.append(f"  {result['details'][key]}")

        lines.append('')
        lines.append("【第二问: 生意模式好吗？】")
        lines.append(f"  评分: {result['scores']['business']}/5")
        for key in ['debt', 'cash', 'moat']:
            if key in result['details']:
                lines.append(f"  {result['details'][key]}")

        lines.append('')
        lines.append("【第三问: 价格合理吗？】")
        lines.append(f"  评分: {result['scores']['valuation']}/3")
        if 'valuation' in result['details']:
            lines.append(f"  {result['details']['valuation']}")
        if 'pb' in result['details']:
            lines.append(f"  {result['details']['pb']}")

        # 结论
        lines.append('')
        lines.append(f"{'='*50}")
        lines.append(f"🎯 结论: {result['conclusion']}")
        if result['stop_loss']:
            lines.append(f"   止损价: {result['stop_loss']} 元 (-8%)")
        if result['target_price']:
            lines.append(f"   目标价: {result['target_price']} 元")

        # 风险提示
        lines.append('')
        lines.append("⚠️ 风险提示:")
        lines.append("  • 投资有风险，以上分析仅供参考，不构成投资建议")
        lines.append("  • 严格执行止损，跌破止损价立即卖出")
        lines.append("  • 单只股票不超过总仓位 20%")

        return '\n'.join(lines)


class SerenityBottleneckAnalyzer:
    """Serenity供应链瓶颈筛选器
    
    核心哲学: 不买AI龙头，狙击产业链中最短的板
    
    五维筛选: 物理不可替代性/供应集中度/技术壁垒/扩产周期/需求刚性
    每维度0-2分，总分≥8纳入关注，≥9为核心瓶颈
    """

    # 六大瓶颈环节定义
    BOTTLENECK_SEGMENTS = {
        'advanced_packaging': {
            'name': '先进封装',
            'stars': 5,
            'logic': 'CoWoS产能缺口30%，封装成AI芯片最核心瓶颈',
            'stocks': [('600584', '长电科技'), ('002156', '通富微电')],
        },
        'optical_cpo': {
            'name': '光通信/CPO',
            'stars': 5,
            'logic': 'GB200需18万只光模块，CPO是I/O唯一解',
            'stocks': [('300308', '中际旭创'), ('300394', '天孚通信')],
        },
        'semiconductor_equipment': {
            'name': '半导体设备',
            'stars': 5,
            'logic': '国产化率24%，设备交期18-24个月',
            'stocks': [('688012', '中微公司'), ('688072', '拓荆科技'), ('688120', '华海清科')],
        },
        'semiconductor_materials': {
            'name': '半导体材料',
            'stars': 5,
            'logic': '光刻胶/特气国产化率<10%',
            'stocks': [('301269', '华大九天'), ('300346', '南大光电')],
        },
        'liquid_cooling': {
            'name': '液冷散热',
            'stars': 4,
            'logic': '芯片功耗>1000W，风冷已达物理极限',
            'stocks': [('002837', '英维克'), ('688170', '江南新材')],
        },
        'hbm_storage': {
            'name': 'HBM/存储',
            'stars': 4,
            'logic': '全球仅3家原厂，A股无直接标的',
            'stocks': [('000021', '深科技'), ('688008', '澜起科技')],
        },
    }

    def screen(self, ds: DataSource = None) -> dict:
        """执行瓶颈筛选: 对六大环节标的进行基本面+技术面双重验证"""
        if ds is None:
            ds = DataSource()

        results = {}
        all_codes = []
        for seg_key, seg in self.BOTTLENECK_SEGMENTS.items():
            for code, name in seg['stocks']:
                all_codes.append(code)

        # 批量获取实时行情
        realtime = ds.fetch_realtime(all_codes)
        
        # 基本面筛选
        duan = DuanYongpingAnalyzer()

        for seg_key, seg in self.BOTTLENECK_SEGMENTS.items():
            seg_results = []
            for code, name in seg['stocks']:
                price_data = realtime.get(code, {})
                financial = duan.analyze(code, ds)
                
                # 技术分析
                klines = ds.fetch_kline(code, 30)
                ta_result = {}
                if klines and len(klines) >= 20:
                    ta = TechnicalAnalyzer()
                    ta_result = ta.analyze(klines)
                
                # 综合判断: 段永平评分 + 技术评分
                duan_score = financial.get('total_score', 0)
                ta_score = ta_result.get('score', {}).get('value', 0)
                
                # 市场认知度判断
                pe = financial.get('financial_raw', {}).get('pe_ttm', 0) or 0
                if pe > 0:
                    if pe >= 50:
                        market_awareness = '已确认'
                        action = '等回调'
                    elif pe >= 30:
                        market_awareness = '认知差'
                        action = '回调即买'
                    else:
                        market_awareness = '最佳买点'
                        action = '立即关注'
                else:
                    market_awareness = '数据不足'
                    action = '观望'

                seg_results.append({
                    'code': code,
                    'name': name,
                    'price': price_data.get('price', 0),
                    'prev_close': price_data.get('prev_close', 0),
                    'change_pct': price_data.get('change_pct', 0) or 
                                  (price_data.get('prev_close', 0) > 0 and 
                                   (price_data.get('price', 0) - price_data.get('prev_close', 0)) / price_data.get('prev_close', 0) * 100) or 0,
                    'duan_score': duan_score,
                    'duan_level': financial.get('level', ''),
                    'ta_score': ta_score,
                    'pe': pe,
                    'market_awareness': market_awareness,
                    'action': action,
                    'stop_loss': financial.get('stop_loss', ''),
                })

            results[seg_key] = {
                'segment_name': seg['name'],
                'stars': seg['stars'],
                'logic': seg['logic'],
                'stocks': seg_results,
            }

        return results

    def format_screen_report(self, results: dict) -> str:
        """格式化瓶颈筛选报告"""
        lines = []
        lines.append(f"{'='*55}")
        lines.append(f"🔍 Serenity供应链瓶颈筛选报告")
        lines.append(f"{'='*55}")
        lines.append(f"核心哲学: 不买AI龙头，狙击产业链中最短的板")
        lines.append('')

        for seg_key, seg in results.items():
            stars_text = '⭐' * seg['stars']
            lines.append(f"【{seg['segment_name']}】 {stars_text}")
            lines.append(f"  逻辑: {seg['logic']}")
            lines.append('')

            for stock in seg['stocks']:
                price = stock.get('price', 0) or stock.get('prev_close', 0)
                change = stock.get('change_pct', 0)
                is_closed = stock.get('price', 0) == 0 and stock.get('prev_close', 0) > 0
                duan_score = stock.get('duan_score', 0)
                ta_score = stock.get('ta_score', 0)
                
                # 判断综合信号
                if duan_score >= 10 and ta_score >= 20:
                    signal = '✅ 买入'
                elif duan_score >= 7 or ta_score >= 10:
                    signal = '⚠️ 观望'
                else:
                    signal = '❌ 回避'

                if is_closed:
                    price_str = f"¥{stock.get('prev_close', 0):.2f} (收盘价)"
                else:
                    price_str = f"¥{price:.2f} ({change:+.2f}%)"
                lines.append(f"  {signal} {stock['name']}({stock['code']}) "
                             f"{price_str} "
                             f"基本面:{duan_score}/15 技术面:{ta_score} "
                             f"认知度:{stock['market_awareness']} → {stock['action']}")
                if stock.get('stop_loss'):
                    lines.append(f"     止损: {stock['stop_loss']}元 (-8%)")
            lines.append('')

        # 操作纪律
        lines.append(f"{'='*55}")
        lines.append("📌 操作纪律:")
        lines.append("  • 总仓位≤25%，单只≤15%")
        lines.append("  • 止损-8%，不追涨停板")
        lines.append("  • 分批建仓（3-5次)")
        lines.append('')
        lines.append("⚠️ 风险提示: 以上分析仅供参考，不构成投资建议")

        return '\n'.join(lines)


# ============ 三维综合分析 ============

def full_analysis(code: str) -> str:
    """执行三维综合分析: 基本面+技术面+资金面"""
    ds = DataSource()
    
    # 基本面 (段永平框架)
    duan = DuanYongpingAnalyzer()
    fundamental = duan.analyze(code, ds)
    
    # 技术面
    ta = TechnicalAnalyzer()
    klines = ds.fetch_kline(code, 30)
    ta_result = ta.analyze(klines) if klines and len(klines) >= 20 else {}
    
    # 实时行情
    realtime = ds.fetch_realtime([code])
    price_data = realtime.get(code, {})
    
    # 综合判断
    duan_score = fundamental.get('total_score', 0)
    ta_score = ta_result.get('score', {}).get('value', 0)
    
    if duan_score >= 10 and ta_score >= 20:
        action = '买入'
        action_detail = '✅ 基本面+技术面共振，强买入信号'
    elif duan_score >= 7 and ta_score >= 10:
        action = '观望'
        action_detail = '⚠️ 基本面尚可，技术面待确认'
    elif duan_score < 4:
        action = '回避'
        action_detail = '❌ 基本面不佳，回避'
    else:
        action = '观望'
        action_detail = '⚠️ 信号不明确，建议观望'
    
    # 生成报告
    lines = []
    lines.append(f"{'='*55}")
    lines.append(f"📊 三维综合分析 · {fundamental.get('name', code)} ({code})")
    lines.append(f"{'='*55}")
    
    price = price_data.get('price', 0) or price_data.get('prev_close', 0)
    prev_close = price_data.get('prev_close', 0)
    current_price = price_data.get('price', 0)
    is_closed = (current_price == 0 and prev_close > 0)  # 非交易时段
    if price_data.get('source') == 'eastmoney_fundgz':
        change_pct = price_data.get('change_pct', 0)
    elif prev_close > 0 and current_price > 0:
        change_pct = (current_price - prev_close) / prev_close * 100
    else:
        change_pct = 0
    
    color = '🔴' if change_pct > 0 else '🟢' if change_pct < 0 else '⚪'
    if is_closed:
        lines.append(f"💰 {prev_close:.2f} 元 (收盘价 · 非交易时段)")
    else:
        lines.append(f"💰 {color} {price:.2f} 元 ({change_pct:+.2f}%)")
    lines.append('')

    # 基本面
    lines.append("【基本面 · 段永平框架】")
    lines.append(f"  评分: {duan_score}/{fundamental.get('max_score', 15)}")
    for key in ['roe', 'growth', 'margin', 'debt', 'moat', 'valuation']:
        if key in fundamental.get('details', {}):
            lines.append(f"  {fundamental['details'][key]}")
    lines.append('')

    # 技术面
    if ta_result:
        lines.append("【技术面】")
        score_info = ta_result.get('score', {})
        lines.append(f"  综合评分: {score_info.get('value', 0)} {score_info.get('level', '')}")
        suggestion = ta_result.get('suggestion', '')
        if suggestion:
            lines.append(f"  操盘建议: {suggestion}")
        # MA/MACD/RSI
        for key in ['ma_signal', 'macd_signal', 'rsi_signal']:
            if key in ta_result:
                lines.append(f"  {ta_result[key]}")
    lines.append('')

    # 买卖建议
    lines.append(f"{'='*55}")
    lines.append(f"🎯 操作: {action}")
    lines.append(f"   {action_detail}")
    if fundamental.get('stop_loss') and price > 0:
        lines.append(f"   买入价: ≤{price:.2f}元")
        lines.append(f"   止损价: {fundamental['stop_loss']}元 (-8%)")
        if fundamental.get('target_price'):
            lines.append(f"   目标价: {fundamental['target_price']}元")

    lines.append('')
    lines.append("⚠️ 风险提示: 投资有风险，以上分析仅供参考，不构成投资建议")
    lines.append("   严格执行止损，单只股票不超过总仓位20%")

    return '\n'.join(lines)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='选股策略分析')
    parser.add_argument('--analyze', help='分析单只股票 (段永平+技术面)')
    parser.add_argument('--serenity', action='store_true', help='执行瓶颈筛选')
    args = parser.parse_args()

    if args.analyze:
        print(full_analysis(args.analyze))
    elif args.serenity:
        analyzer = SerenityBottleneckAnalyzer()
        results = analyzer.screen()
        print(analyzer.format_screen_report(results))
    else:
        # 默认: 测试茅台 + 瓶颈筛选
        print("=== 段永平框架分析 (茅台) ===")
        print(full_analysis('600519'))
        
        print("\n\n=== Serenity瓶颈筛选 ===")
        analyzer = SerenityBottleneckAnalyzer()
        results = analyzer.screen()
        print(analyzer.format_screen_report(results))
