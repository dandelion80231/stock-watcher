#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stock Watcher v2.0 - 监控预警引擎
7大预警规则 + 分级预警 + 操盘手习惯分析
整合自 stock-watcher-cn 的差异化功能
"""
import sys
import io
if not isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import json
import time
import os
from datetime import datetime
from config import (
    DATA_DIR, WATCHLIST_FILE, PORTFOLIO_FILE, ALERT_LOG_FILE,
    CACHE_DIR, TRADER_DB_FILE, STOCK_TYPE, TYPE_THRESHOLDS,
    load_watchlist, load_portfolio, save_portfolio,
    DEFAULT_MONITOR_CONFIG,
)
from data_source import DataSource
from technical_analysis import TechnicalAnalyzer


class AlertEngine:
    """预警引擎 - 7大规则 + 分级系统"""

    def __init__(self):
        self.ds = DataSource()
        self.ta = TechnicalAnalyzer()
        self.alert_log = []  # 30分钟冷却
        self.config = DEFAULT_MONITOR_CONFIG.copy()
        
        # 加载持仓配置
        self.portfolio = load_portfolio()
        
        # 加载自定义监控配置
        from config import load_json, MONITOR_CONFIG_FILE
        custom_config = load_json(MONITOR_CONFIG_FILE)
        self.config.update(custom_config)

    # ============ 7大预警规则 ============

    def check_alerts(self, code: str, data: dict, stock_type: str = 'individual') -> tuple:
        """检查所有预警条件
        返回: (alerts_list, alert_level)
        alerts_list: [(type, text, weight), ...]
        alert_level: 'critical' / 'warning' / 'info' / None
        """
        alerts = []
        weights = []
        
        portfolio_entry = self.portfolio.get(code, {})
        cost = portfolio_entry.get('cost', 0)
        alerts_config = portfolio_entry.get('alerts', {})
        
        # 获取类型阈值
        thresholds = TYPE_THRESHOLDS.get(stock_type, TYPE_THRESHOLDS['individual'])
        
        price = data.get('price', 0)
        prev_close = data.get('prev_close', 0)
        # fundgz 数据源直接提供 change_pct，用 prev_nav 近似 prev_close
        if data.get('source') == 'eastmoney_fundgz':
            change_pct = data.get('change_pct', 0)
            prev_close = data.get('prev_nav', price) if prev_close <= 0 else prev_close
        elif prev_close > 0:
            change_pct = (price - prev_close) / prev_close * 100
        else:
            change_pct = 0
            return ([], None)
        
        if price <= 0:
            return ([], None)
        
        # ---- 规则1: 成本百分比预警 (权重3) ----
        if cost and cost > 0:
            cost_change_pct = (price - cost) / cost * 100
            
            pct_above = alerts_config.get('cost_pct_above', thresholds.get('change_pct_default', 15))
            pct_below = alerts_config.get('cost_pct_below', -thresholds.get('change_pct_default', 12))
            
            if cost_change_pct >= pct_above and not self._alerted_recently(code, 'cost_above'):
                target = cost * (1 + pct_above/100)
                alerts.append(('cost_above', f"🎯 盈利 {pct_above:.0f}% (目标价 ¥{target:.2f})", 3))
                weights.append(3)
            
            if cost_change_pct <= pct_below and not self._alerted_recently(code, 'cost_below'):
                target = cost * (1 + pct_below/100)
                alerts.append(('cost_below', f"🛑 亏损 {abs(pct_below):.0f}% (止损价 ¥{target:.2f})", 3))
                weights.append(3)
        
        # ---- 规则2: 日内涨跌幅预警 (权重1-3) ----
        pct_up = alerts_config.get('change_pct_above', thresholds.get('change_pct_default'))
        pct_down = alerts_config.get('change_pct_below', -thresholds.get('change_pct_default'))
        
        if pct_up and change_pct >= pct_up and not self._alerted_recently(code, 'pct_up'):
            if change_pct >= 7:
                w = 3  # 涨停附近
            elif change_pct >= 5:
                w = 2
            else:
                w = 1
            alerts.append(('pct_up', f"📈 日内大涨 {change_pct:+.2f}%", w))
            weights.append(w)
        
        if pct_down and change_pct <= pct_down and not self._alerted_recently(code, 'pct_down'):
            if change_pct <= -7:
                w = 3
            elif change_pct <= -5:
                w = 2
            else:
                w = 1
            alerts.append(('pct_down', f"📉 日内大跌 {change_pct:+.2f}%", w))
            weights.append(w)
        
        # ---- 规则3: 成交量异动 (权重2) ----
        if stock_type != 'gold' and data.get('volume', 0) > 0:
            volume_threshold = alerts_config.get('volume_surge', thresholds.get('volume_surge_default', 2))
            if volume_threshold:
                klines = self.ds.fetch_kline(code, 6)
                if klines and len(klines) >= 6:
                    # 前5日均量
                    ma5_vol = sum(k['volume'] for k in klines[:5]) / 5
                    current_vol = data.get('volume', 0)
                    if ma5_vol > 0:
                        ratio = current_vol / ma5_vol
                        if ratio >= volume_threshold and not self._alerted_recently(code, 'volume_surge'):
                            alerts.append(('volume_surge', f"📊 放量 {ratio:.1f}倍 (5日均量)", 2))
                            weights.append(2)
                        elif ratio <= 0.5 and not self._alerted_recently(code, 'volume_shrink'):
                            alerts.append(('volume_shrink', f"📉 缩量 {ratio:.1f}倍", 1))
                            weights.append(1)
        
        # ---- 规则4: 均线金叉/死叉 (权重3) ----
        if stock_type != 'gold' and alerts_config.get('ma_monitor', True):
            klines = self.ds.fetch_kline(code, 30)
            if klines and len(klines) >= 20:
                ta_result = self.ta.analyze(klines)
                ma = ta_result.get('ma', {})
                
                if ma.get('golden_cross') and not self._alerted_recently(code, 'ma_golden'):
                    alerts.append(('ma_golden',
                        f"🌟 均线金叉 (MA5¥{ma['MA5']:.2f}上穿MA10¥{ma['MA10']:.2f})", 3))
                    weights.append(3)
                
                if ma.get('death_cross') and not self._alerted_recently(code, 'ma_death'):
                    alerts.append(('ma_death',
                        f"⚠️ 均线死叉 (MA5¥{ma['MA5']:.2f}下穿MA10¥{ma['MA10']:.2f})", 3))
                    weights.append(3)
                
                # RSI超买超卖
                rsi = ta_result.get('rsi', {})
                rsi_val = rsi.get('value')
                if rsi_val:
                    if rsi_val > thresholds.get('rsi_overbought', 70) and not self._alerted_recently(code, 'rsi_high'):
                        alerts.append(('rsi_high', f"🔥 RSI超买 ({rsi_val})，可能回调", 2))
                        weights.append(2)
                    elif rsi_val < thresholds.get('rsi_oversold', 30) and not self._alerted_recently(code, 'rsi_low'):
                        alerts.append(('rsi_low', f"❄️ RSI超卖 ({rsi_val})，可能反弹", 2))
                        weights.append(2)
        
        # ---- 规则5: 跳空缺口 (权重2) ----
        if stock_type != 'gold' and alerts_config.get('gap_monitor', True):
            klines = self.ds.fetch_kline(code, 2)
            if klines and len(klines) >= 2:
                gap = self.ta._detect_gap(klines)
                if gap.get('gap') == 'up' and not self._alerted_recently(code, 'gap_up'):
                    alerts.append(('gap_up', f"⬆️ 向上跳空 {gap['gap_pct']:.1f}%", 2))
                    weights.append(2)
                elif gap.get('gap') == 'down' and not self._alerted_recently(code, 'gap_down'):
                    alerts.append(('gap_down', f"⬇️ 向下跳空 {gap['gap_pct']:.1f}%", 2))
                    weights.append(2)
        
        # ---- 规则6: 动态止盈 (权重2-3) ----
        if cost and cost > 0 and alerts_config.get('trailing_stop', True):
            profit_pct = (price - cost) / cost * 100
            if profit_pct >= 10:
                # 从最高价回撤
                high = data.get('high', price)
                drawdown = (high - price) / high * 100 if high > cost else 0
                
                if drawdown >= 5 and not self._alerted_recently(code, 'trailing_5'):
                    alerts.append(('trailing_5', f"📉 利润回撤 {drawdown:.1f}%，建议减仓", 2))
                    weights.append(2)
                elif drawdown >= 10 and not self._alerted_recently(code, 'trailing_10'):
                    alerts.append(('trailing_10', f"🚨 利润回撤 {drawdown:.1f}%，建议清仓", 3))
                    weights.append(3)
        
        # ---- 规则7: 操盘手行为分析 (权重3) ----
        if stock_type != 'gold' and alerts_config.get('trader_monitor', True):
            abnormal = self._detect_trader_abnormal(code, data)
            for behavior in abnormal:
                alerts.append(('trader_abnormal', behavior, 3))
                weights.append(3)
        
        # 计算预警级别
        level = self._calc_level(alerts, weights)
        
        return (alerts, level)

    def _calc_level(self, alerts, weights):
        """分级: critical(紧急) / warning(警告) / info(提醒)"""
        if not alerts:
            return None
        
        total_weight = sum(w for _, _, w in alerts)
        count = len(alerts)
        
        if total_weight >= 5 or count >= 3:
            return 'critical'
        elif total_weight >= 3 or count >= 2:
            return 'warning'
        else:
            return 'info'

    # ============ 操盘手行为检测 ============

    def _detect_trader_abnormal(self, code: str, data: dict) -> list:
        """检测操盘手异常行为 (简化版，不需要 SQLite)"""
        abnormalities = []
        
        # 1. 量价背离: 放量但价格不动
        vol = data.get('volume', 0)
        price = data.get('price', 0)
        prev_close = data.get('prev_close', 0)
        if vol > 0 and prev_close > 0:
            change_pct = abs((price - prev_close) / prev_close * 100)
            klines = self.ds.fetch_kline(code, 6)
            if klines and len(klines) >= 6:
                ma5_vol = sum(k['volume'] for k in klines[:5]) / 5
                if ma5_vol > 0 and vol / ma5_vol >= 2.0 and change_pct < 1.5:
                    abnormalities.append("📊 量价背离：放量但涨幅不足1.5%，警惕主力出货")
        
        # 2. 收盘急拉/跳水 (价格偏离日内均价)
        if prev_close > 0:
            open_price = data.get('open', price)
            mid_price = (data.get('high', price) + data.get('low', price)) / 2
            if abs(price - mid_price) / mid_price * 100 > 2:
                if price > mid_price:
                    abnormalities.append("⚡ 收盘急拉：价格远高于日内均价，可能诱多")
                else:
                    abnormalities.append("⚡ 收盘跳水：价格远低于日内均价，可能诱空")
        
        return abnormalities

    # ============ 冷却机制 ============

    def _alerted_recently(self, code: str, alert_type: str) -> bool:
        """同类预警30分钟内只发一次"""
        now = time.time()
        cooldown = self.config.get('alert_cooldown_minutes', 30) * 60
        self.alert_log = [l for l in self.alert_log if now - l['t'] < cooldown]
        for l in self.alert_log:
            if l['c'] == code and l['a'] == alert_type:
                return True
        return False

    def _record_alert(self, code: str, alert_type: str):
        self.alert_log.append({'c': code, 'a': alert_type, 't': time.time()})

    # ============ 消息格式化 ============

    def format_alert_message(self, code: str, data: dict, alerts: list, level: str) -> str:
        """格式化预警消息 (飞书/微信/终端)"""
        price = data.get('price', 0)
        prev_close = data.get('prev_close', 0)
        # fundgz 数据源兼容
        if data.get('source') == 'eastmoney_fundgz':
            change_pct = data.get('change_pct', 0)
        elif prev_close > 0:
            change_pct = (price - prev_close) / prev_close * 100
        else:
            change_pct = 0
        
        # 红涨绿跌
        color = '🔴' if change_pct > 0 else '🟢' if change_pct < 0 else '⚪'
        
        # 预警级别图标
        level_icon = {'critical': '🚨', 'warning': '⚠️', 'info': '📢'}.get(level, '📢')
        level_text = {'critical': '【紧急】', 'warning': '【警告】', 'info': '【提醒】'}.get(level, '')
        
        name = data.get('name', code)
        unit = data.get('unit', '元')
        
        msg = f"{level_icon} {level_text}{color} {name} ({code})\n"
        msg += "━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"💰 当前价格: {price:.4f} {unit} ({change_pct:+.2f}%)\n"
        
        # 持仓盈亏
        portfolio_entry = self.portfolio.get(code, {})
        cost = portfolio_entry.get('cost', 0)
        if cost > 0:
            cost_change = (price - cost) / cost * 100
            profit_icon = '🔴+' if cost_change > 0 else '🟢'
            msg += f"📊 持仓成本: ¥{cost:.2f} | 盈亏: {profit_icon}{cost_change:.2f}%\n"
        
        msg += f"\n🎯 触发预警 ({len(alerts)}项):\n"
        for atype, text, weight in alerts:
            msg += f"  • {text}\n"
            self._record_alert(code, atype)
        
        # 技术分析摘要
        stock_type = self.ds.identify_stock_type(code)
        if stock_type != 'gold':
            klines = self.ds.fetch_kline(code, 30)
            if klines and len(klines) >= 20:
                ta_result = self.ta.analyze(klines)
                score = ta_result.get('score', {})
                msg += f"\n💡 操盘建议: {ta_result.get('suggestion', '')}\n"
                msg += f"   综合评分: {score.get('value', 0)} {score.get('level', '')}\n"
        
        return msg

    # ============ 执行监控 ============

    def run_once(self, watchlist: list = None, include_specials: list = None) -> list:
        """执行一次监控扫描
        返回: [alert_message_string, ...]
        """
        if watchlist is None:
            watchlist = load_watchlist()
        
        if not watchlist:
            return []
        
        codes = [s['code'] for s in watchlist]
        data_map = self.ds.fetch_realtime(codes, include_specials)
        
        triggered = []
        
        for stock in watchlist:
            code = stock['code']
            if code not in data_map:
                continue
            
            data = data_map[code]
            stock_type = stock.get('type', self.ds.identify_stock_type(code))
            
            alerts, level = self.check_alerts(code, data, stock_type)
            
            if alerts:
                msg = self.format_alert_message(code, data, alerts, level)
                triggered.append(msg)
        
        return triggered

    # ============ 收盘总结 ============

    def generate_daily_summary(self, watchlist: list = None, include_specials: list = None) -> str:
        """生成收盘总结"""
        if watchlist is None:
            watchlist = load_watchlist()
        
        if not watchlist:
            return "无自选股"
        
        codes = [s['code'] for s in watchlist]
        data_map = self.ds.fetch_realtime(codes, include_specials)
        
        now = datetime.now()
        lines = []
        lines.append('=' * 50)
        lines.append(f'📊 收盘总结 ({now.strftime("%Y-%m-%d %H:%M")})')
        lines.append('=' * 50)
        
        triggered = []
        for stock in watchlist:
            code = stock['code']
            if code not in data_map:
                continue
            
            data = data_map[code]
            price = data.get('price', 0)
            prev_close = data.get('prev_close', 0)
            # fundgz 数据源兼容
            if data.get('source') == 'eastmoney_fundgz':
                change_pct = data.get('change_pct', 0)
            elif prev_close > 0:
                change_pct = (price - prev_close) / prev_close * 100
            else:
                change_pct = 0
            color = '🔴' if change_pct > 0 else '🟢' if change_pct < 0 else '⚪'
            name = data.get('name', code)
            unit = data.get('unit', '元')
            
            stock_type = stock.get('type', self.ds.identify_stock_type(code))
            alerts, level = self.check_alerts(code, data, stock_type)
            
            lines.append(f'\n{color} {name} ({code})')
            lines.append(f'   价格: {price:.4f} {unit} ({change_pct:+.2f}%)')
            
            if alerts:
                level_icon = {'critical': '🚨', 'warning': '⚠️', 'info': '📢'}.get(level, '📢')
                lines.append(f'   {level_icon} 预警({len(alerts)}项):')
                for _, text, _ in alerts:
                    lines.append(f'     • {text}')
                triggered.append((stock, data, alerts, level))
            else:
                lines.append('   ↔️ 无预警')
            
            # 技术分析
            if stock_type != 'gold':
                klines = self.ds.fetch_kline(code, 30)
                if klines and len(klines) >= 20:
                    ta_result = self.ta.analyze(klines)
                    score = ta_result.get('score', {})
                    lines.append(f'   评分: {score.get("value", 0)} {score.get("level", "")}')
        
        lines.append('\n' + '=' * 50)
        lines.append('💡 明日关注:')
        lines.append('   - 持续关注成交量异动股票')
        lines.append('   - 关注均线金叉/死叉信号')
        lines.append('=' * 50)
        
        return '\n'.join(lines)


if __name__ == '__main__':
    engine = AlertEngine()
    
    # 测试1: 监控扫描
    print("=== 监控扫描测试 ===")
    watchlist = load_watchlist()
    if watchlist:
        for msg in engine.run_once(watchlist, include_specials=['XAUUSD']):
            print(msg)
    else:
        print("自选股列表为空，请先添加股票")
    
    # 测试2: 收盘总结
    print("\n=== 收盘总结测试 ===")
    if watchlist:
        summary = engine.generate_daily_summary(watchlist, include_specials=['XAUUSD'])
        print(summary)
