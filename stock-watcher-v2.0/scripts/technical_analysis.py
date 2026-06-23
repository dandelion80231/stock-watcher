#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stock Watcher v2.0 - 技术分析模块
支持 MA均线、RSI、MACD、布林带、跳空缺口、动态止盈
"""
import sys
import io
if not isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from config import (
    TA_MA_PERIODS, TA_RSI_PERIOD,
    TA_MACD_FAST, TA_MACD_SLOW, TA_MACD_SIGNAL,
    TA_BOLL_PERIOD, TA_BOLL_STD,
)


class TechnicalAnalyzer:
    """技术分析引擎"""

    def analyze(self, klines: list) -> dict:
        """综合技术分析
        klines: [{date, open, close, high, low, volume, amount}, ...]
        至少需要30条K线数据
        """
        if len(klines) < 20:
            return {'sufficient_data': False, 'reason': f'K线数据不足({len(klines)}条)，需至少20条'}

        closes = [k['close'] for k in klines]
        highs = [k['high'] for k in klines]
        lows = [k['low'] for k in klines]
        volumes = [k['volume'] for k in klines]
        opens = [k['open'] for k in klines]

        result = {
            'sufficient_data': True,
            'ma': self._calc_ma(closes),
            'rsi': self._calc_rsi(closes),
            'macd': self._calc_macd(closes),
            'boll': self._calc_boll(closes),
            'volume_ratio': self._calc_volume_ratio(volumes),
            'gap': self._detect_gap(klines),
            'trend': self._detect_trend(closes, highs, lows),
        }

        # 综合评分
        result['score'] = self._calc_score(result)
        result['suggestion'] = self._gen_suggestion(result)

        return result

    # ============ MA 均线系统 ============

    def _calc_ma(self, closes: list) -> dict:
        """计算移动均线和金叉/死叉"""
        ma_data = {}
        
        for period in TA_MA_PERIODS:
            if len(closes) >= period:
                ma_data[f'MA{period}'] = sum(closes[-period:]) / period
        
        # 金叉/死叉检测 (MA5 vs MA10)
        if len(closes) >= 11:
            prev_ma5 = sum(closes[-6:-1]) / 5
            prev_ma10 = sum(closes[-11:-1]) / 10
            curr_ma5 = ma_data.get('MA5', 0)
            curr_ma10 = ma_data.get('MA10', 0)
            
            # 金叉: MA5从下方穿越MA10
            ma_data['golden_cross'] = prev_ma5 <= prev_ma10 and curr_ma5 > curr_ma10
            # 死叉: MA5从上方穿越MA10
            ma_data['death_cross'] = prev_ma5 >= prev_ma10 and curr_ma5 < curr_ma10
            
            # 趋势排列
            ma5 = ma_data.get('MA5', 0)
            ma10 = ma_data.get('MA10', 0)
            ma20 = ma_data.get('MA20', 0)
            
            if ma5 > ma10 > ma20:
                ma_data['arrangement'] = '多头排列 📈'
            elif ma5 < ma10 < ma20:
                ma_data['arrangement'] = '空头排列 📉'
            else:
                ma_data['arrangement'] = '交叉震荡 ↔️'
        
        return ma_data

    # ============ RSI ============

    def _calc_rsi(self, closes: list, period: int = None) -> dict:
        """计算RSI指标"""
        period = period or TA_RSI_PERIOD
        if len(closes) < period + 1:
            return {'value': None, 'signal': '数据不足'}
        
        gains = []
        losses = []
        for i in range(1, period + 1):
            change = closes[-i] - closes[-i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        
        if avg_loss == 0:
            rsi = 100
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
        
        rsi = round(rsi, 2)
        
        if rsi > 70:
            signal = '超买 🔥 (可能回调)'
        elif rsi > 60:
            signal = '偏强 ✅'
        elif rsi < 30:
            signal = '超卖 ❄️ (可能反弹)'
        elif rsi < 40:
            signal = '偏弱 ⚠️'
        else:
            signal = '中性 ↔️'
        
        return {'value': rsi, 'signal': signal}

    # ============ MACD ============

    def _calc_macd(self, closes: list) -> dict:
        """计算MACD指标"""
        if len(closes) < TA_MACD_SLOW + TA_MACD_SIGNAL:
            return {'macd': None, 'signal': '数据不足'}
        
        # 计算EMA
        def ema(data, period):
            multiplier = 2 / (period + 1)
            ema_val = data[0]
            for price in data[1:]:
                ema_val = (price - ema_val) * multiplier + ema_val
            return ema_val
        
        # 近期数据用于计算
        recent = closes[-(TA_MACD_SLOW + TA_MACD_SIGNAL):]
        
        ema_fast = ema(recent, TA_MACD_FAST)
        ema_slow = ema(recent, TA_MACD_SLOW)
        macd_line = ema_fast - ema_slow
        
        # 简化: 用最近几天的MACD值近似信号线
        # 精确计算需要历史MACD序列
        macd_values = []
        for i in range(TA_MACD_SIGNAL, len(recent)):
            sub = recent[:i+1]
            e_f = ema(sub, TA_MACD_FAST)
            e_s = ema(sub, TA_MACD_SLOW)
            macd_values.append(e_f - e_s)
        
        signal_line = ema(macd_values, TA_MACD_SIGNAL) if len(macd_values) >= TA_MACD_SIGNAL else macd_line
        histogram = macd_line - signal_line
        
        # 判断MACD信号
        if histogram > 0 and macd_line > 0:
            signal = '多头 📈'
        elif histogram < 0 and macd_line < 0:
            signal = '空头 📉'
        elif histogram > 0 and macd_line < 0:
            signal = '转强 🔄'
        elif histogram < 0 and macd_line > 0:
            signal = '转弱 ⚠️'
        else:
            signal = '中性 ↔️'
        
        return {
            'macd': round(macd_line, 4),
            'signal_line': round(signal_line, 4),
            'histogram': round(histogram, 4),
            'signal': signal,
        }

    # ============ 布林带 ============

    def _calc_boll(self, closes: list) -> dict:
        """计算布林带"""
        if len(closes) < TA_BOLL_PERIOD:
            return {'upper': None, 'middle': None, 'lower': None, 'signal': '数据不足'}
        
        recent = closes[-TA_BOLL_PERIOD:]
        middle = sum(recent) / TA_BOLL_PERIOD
        
        # 标准差
        variance = sum((x - middle) ** 2 for x in recent) / TA_BOLL_PERIOD
        std = variance ** 0.5
        
        upper = middle + TA_BOLL_STD * std
        lower = middle - TA_BOLL_STD * std
        
        current = closes[-1]
        
        # 判断位置
        if current >= upper:
            position = '突破上轨 🔥 (超买)'
        elif current <= lower:
            position = '突破下轨 ❄️ (超卖)'
        elif current > middle:
            position = '中轨上方 ✅'
        else:
            position = '中轨下方 ⚠️'
        
        return {
            'upper': round(upper, 2),
            'middle': round(middle, 2),
            'lower': round(lower, 2),
            'current': current,
            'position': position,
        }

    # ============ 成交量分析 ============

    def _calc_volume_ratio(self, volumes: list) -> dict:
        """计算成交量比率 (当前量/5日均量)"""
        if len(volumes) < 6:
            return {'ratio': None, 'signal': '数据不足'}
        
        ma5_vol = sum(volumes[-6:-1]) / 5  # 前5日均量
        current_vol = volumes[-1]
        ratio = current_vol / ma5_vol if ma5_vol > 0 else 0
        
        if ratio >= 3:
            signal = '巨量 🚨'
        elif ratio >= 2:
            signal = '放量 ✅'
        elif ratio >= 1.5:
            signal = '温和放量 ↔️'
        elif ratio <= 0.5:
            signal = '严重缩量 ⚠️'
        elif ratio <= 0.7:
            signal = '缩量 📉'
        else:
            signal = '正常 ↔️'
        
        return {
            'ratio': round(ratio, 2),
            'ma5_volume': round(ma5_vol, 2),
            'current_volume': current_vol,
            'signal': signal,
        }

    # ============ 跳空缺口 ============

    def _detect_gap(self, klines: list) -> dict:
        """检测跳空缺口"""
        if len(klines) < 2:
            return {'gap': None, 'signal': '数据不足'}
        
        today = klines[-1]
        yesterday = klines[-2]
        
        today_open = today['open']
        yesterday_high = yesterday['high']
        yesterday_low = yesterday['low']
        
        # 向上跳空: 今日开盘 > 昨日最高
        if today_open > yesterday_high * 1.01:
            gap_pct = (today_open - yesterday_high) / yesterday_high * 100
            return {
                'gap': 'up',
                'gap_pct': round(gap_pct, 2),
                'signal': f'向上跳空 {gap_pct:.1f}% ⬆️',
            }
        
        # 向下跳空: 今日开盘 < 昨日最低
        if today_open < yesterday_low * 0.99:
            gap_pct = (yesterday_low - today_open) / yesterday_low * 100
            return {
                'gap': 'down',
                'gap_pct': round(gap_pct, 2),
                'signal': f'向下跳空 {gap_pct:.1f}% ⬇️',
            }
        
        return {'gap': None, 'signal': '无缺口 ↔️'}

    # ============ 趋势判断 ============

    def _detect_trend(self, closes: list, highs: list, lows: list) -> dict:
        """判断短期趋势"""
        if len(closes) < 10:
            return {'direction': 'unknown', 'strength': 0}
        
        # 最近5日趋势
        recent_5 = closes[-5:]
        first_5 = recent_5[0]
        last_5 = recent_5[-1]
        change_5 = (last_5 - first_5) / first_5 * 100
        
        if change_5 > 2:
            direction = 'up'
            strength = min(abs(change_5) / 5, 1.0)
        elif change_5 < -2:
            direction = 'down'
            strength = min(abs(change_5) / 5, 1.0)
        else:
            direction = 'sideways'
            strength = 0.3
        
        return {
            'direction': direction,
            'strength': round(strength, 2),
            '5d_change_pct': round(change_5, 2),
            'signal': {
                'up': '上涨趋势 📈',
                'down': '下跌趋势 📉',
                'sideways': '横盘整理 ↔️',
            }.get(direction, '未知'),
        }

    # ============ 综合评分 ============

    def _calc_score(self, result: dict) -> dict:
        """综合评分系统
        多头得分 +100 (强买), 空头得分 -100 (强卖)
        """
        score = 0
        signals = []
        
        # MA趋势 (权重30)
        ma = result.get('ma', {})
        if ma.get('golden_cross'):
            score += 30
            signals.append('均线金叉 ✅')
        elif ma.get('death_cross'):
            score -= 30
            signals.append('均线死叉 ❌')
        arrangement = ma.get('arrangement', '')
        if '多头' in arrangement:
            score += 15
        elif '空头' in arrangement:
            score -= 15
        
        # RSI (权重20)
        rsi = result.get('rsi', {})
        rsi_val = rsi.get('value')
        if rsi_val:
            if rsi_val > 70:
                score -= 20
                signals.append(f'RSI超买({rsi_val}) ⚠️')
            elif rsi_val < 30:
                score += 20
                signals.append(f'RSI超卖({rsi_val}) 💡')
        
        # MACD (权重20)
        macd = result.get('macd', {})
        macd_signal = macd.get('signal', '')
        if '多头' in macd_signal:
            score += 20
        elif '空头' in macd_signal:
            score -= 20
        elif '转强' in macd_signal:
            score += 10
        
        # 成交量 (权重15)
        vol = result.get('volume_ratio', {})
        ratio = vol.get('ratio')
        if ratio:
            if ratio >= 2:
                score += 15
                signals.append('放量确认 ✅')
            elif ratio <= 0.5:
                score -= 5
        
        # 趋势 (权重15)
        trend = result.get('trend', {})
        if trend.get('direction') == 'up':
            score += 15
        elif trend.get('direction') == 'down':
            score -= 15
        
        # 评分等级
        if score >= 60:
            level = '强烈看多 🚀'
        elif score >= 30:
            level = '偏多 ✅'
        elif score >= 10:
            level = '中性偏多 ↔️'
        elif score >= -10:
            level = '中性 ↔️'
        elif score >= -30:
            level = '中性偏空 ⚠️'
        elif score >= -60:
            level = '偏空 ❌'
        else:
            level = '强烈看空 💀'
        
        return {
            'value': score,
            'level': level,
            'signals': signals,
        }

    def _gen_suggestion(self, result: dict) -> str:
        """生成操盘建议"""
        score = result.get('score', {})
        score_val = score.get('value', 0)
        signals = score.get('signals', [])
        
        if score_val >= 60:
            return '🚀 多条件共振，趋势强劲，可考虑持有或分批加仓'
        elif score_val >= 30:
            return '✅ 趋势向好，可继续持有，关注回调加仓机会'
        elif score_val >= 10:
            return '↔️ 趋势中性偏多，观望为主，等待明确信号'
        elif score_val >= -10:
            return '↔️ 趋势不明，建议观望，不急于操作'
        elif score_val >= -30:
            return '⚠️ 趋势偏弱，注意风险，考虑减仓'
        elif score_val >= -60:
            return '❌ 趋势走弱，建议减仓或离场观望'
        else:
            return '💀 多条件共振偏空，建议及时止损离场'


if __name__ == '__main__':
    from data_source import DataSource
    
    ds = DataSource()
    ta = TechnicalAnalyzer()
    
    # 测试技术分析
    print("=== 技术分析测试 (600519) ===")
    klines = ds.fetch_kline('600519', 30)
    if klines:
        result = ta.analyze(klines)
        print(f"数据充足: {result.get('sufficient_data')}")
        
        if result.get('sufficient_data'):
            ma = result['ma']
            print(f"均线: MA5={ma.get('MA5', 'N/A'):.2f} MA10={ma.get('MA10', 'N/A'):.2f} MA20={ma.get('MA20', 'N/A'):.2f}")
            print(f"排列: {ma.get('arrangement')}")
            print(f"金叉: {ma.get('golden_cross')} 死叉: {ma.get('death_cross')}")
            
            rsi = result['rsi']
            print(f"RSI: {rsi.get('value')} {rsi.get('signal')}")
            
            macd = result['macd']
            print(f"MACD: {macd.get('macd')} 信号线: {macd.get('signal_line')} {macd.get('signal')}")
            
            vol = result['volume_ratio']
            print(f"量比: {vol.get('ratio')} {vol.get('signal')}")
            
            score = result['score']
            print(f"综合评分: {score.get('value')} {score.get('level')}")
            print(f"建议: {result.get('suggestion')}")
    else:
        print("K线数据获取失败")
