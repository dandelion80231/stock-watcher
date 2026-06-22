#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stock Watcher v2.0 - 数据获取模块
支持多种数据源自动切换，覆盖 A股/ETF/黄金/指数/港股

数据源策略:
1. 新浪 (主): 实时行情，延迟1-3秒，轻量稳定
2. 腾讯 (备): 数据更丰富（含买卖五档），稳定
3. 同花顺 (K线): 历史K线数据，技术分析用
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import requests
import json
import re
import time
from datetime import datetime
from config import (
    SINA_QUOTE_URL, SINA_REFERER, TENCENT_QUOTE_URL,
    TJQKA_KLINE_URL, TJQKA_REFERER,
    get_sina_code, get_market_prefix, get_tencent_code,
    SINA_SPECIAL_CODES, STOCK_TYPE,
    load_watchlist, load_portfolio, save_watchlist,
)
from eastmoney_alt import EastMoneyAltSource


class DataSource:
    """统一数据获取接口 - 自动切换数据源"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        })
        self._sina_ok = True
        self._tencent_ok = True
        self._em_alt = EastMoneyAltSource()  # 东方财富替代数据源

    # ============ 新浪 API (主数据源) ============

    def fetch_sina_batch(self, codes: list, include_specials: list = None) -> dict:
        """新浪批量获取实时行情
        codes: 股票代码列表 (如 ['600519', '000001'])
        include_specials: 特殊品种 (如 ['XAUUSD', 'hf_XAU'])
        返回: {code: {name, price, prev_close, open, high, low, volume, amount, date, time, ...}}
        """
        all_sina_codes = []
        code_map = {}  # sina_code → original_code
        
        for code in codes:
            prefix = get_market_prefix(code)
            sina_code = f"{prefix}{code}"
            all_sina_codes.append(sina_code)
            code_map[sina_code] = code
        
        if include_specials:
            for special in include_specials:
                all_sina_codes.append(special)
                code_map[special] = special
        
        if not all_sina_codes:
            return {}
        
        url = f"{SINA_QUOTE_URL}{','.join(all_sina_codes)}"
        try:
            resp = self.session.get(url, headers={'Referer': SINA_REFERER}, timeout=10)
            resp.encoding = 'gb18030'
            results = {}
            
            for line in resp.text.strip().split(';'):
                if 'hq_str_' not in line or '=' not in line:
                    continue
                # 解析变量名
                var_part = line.split('=')[0]
                sina_code = var_part.split('hq_str_')[-1] if 'hq_str_' in var_part else var_part.split('_')[-1]

                # 解析值
                val_part = line[line.index('"')+1 : line.rindex('"')]
                if not val_part:
                    continue

                original_code = code_map.get(sina_code, sina_code)

                # 判断是特殊品种还是普通A股
                if sina_code in SINA_SPECIAL_CODES or sina_code.startswith('hf_') or sina_code.startswith('XAU') or sina_code.startswith('XAG'):
                    results[original_code] = self._parse_sina_special(sina_code, val_part)
                else:
                    parsed = self._parse_sina_stock(val_part)
                    if parsed:
                        results[original_code] = parsed
            
            self._sina_ok = True
            return results
            
        except Exception as e:
            self._sina_ok = False
            print(f"新浪API失败: {e}")
            return {}

    def _parse_sina_stock(self, val: str) -> dict:
        """解析新浪A股/ETF数据
        格式: 名称,今开,昨收,当前价,最高,最低,竞买,竞卖,成交量,成交额,...,日期,时间,...
        """
        parts = val.split(',')
        if len(parts) < 32:
            return None

        try:
            price = float(parts[3])
            prev_close = float(parts[2])
            if price <= 0 and prev_close <= 0:
                return None

            # 尝试解析换手率（parts[38]）
            turnover_rate = 0.0
            try:
                if len(parts) > 38 and parts[38]:
                    turnover_rate = float(parts[38])
            except (ValueError, IndexError):
                pass

            return {
                'name': parts[0],
                'price': price,
                'prev_close': prev_close,
                'open': float(parts[1]),
                'high': float(parts[4]),
                'low': float(parts[5]),
                'volume': int(float(parts[8])),
                'amount': float(parts[9]),
                'date': parts[30] if len(parts) > 30 else '',
                'time': parts[31] if len(parts) > 31 else '',
                'bid1_price': float(parts[6]) if len(parts) > 6 else 0,
                'ask1_price': float(parts[7]) if len(parts) > 7 else 0,
                'turnover_rate': turnover_rate,
                'source': 'sina',
            }
        except (ValueError, IndexError) as e:
            return None

    def _parse_sina_special(self, sina_code: str, val: str) -> dict:
        """解析新浪特殊品种 (国际金银、伦敦金)
        XAUUSD 格式: 时间,open,high,low,current,volume,...,prev_close,...,unit,date
        hf_XAU 格式: 价格(人民币/克),...
        """
        parts = val.split(',')
        
        if sina_code == 'XAUUSD' and len(parts) >= 11:
            return {
                'name': '国际金价',
                'price': float(parts[3]) if float(parts[3]) > 0 else float(parts[8]),
                'prev_close': float(parts[5]) if len(parts) > 5 else 0,
                'open': float(parts[1]),
                'high': float(parts[6]),
                'low': float(parts[7]),
                'volume': int(float(parts[4])) if len(parts) > 4 else 0,
                'amount': 0,
                'date': parts[10].rstrip('"') if len(parts) > 10 else '',
                'time': parts[0],
                'unit': '美元/盎司',
                'source': 'sina',
                'type': 'gold',
            }
        elif sina_code == 'XAGUSD' and len(parts) >= 11:
            return {
                'name': '国际银价',
                'price': float(parts[3]) if float(parts[3]) > 0 else float(parts[8]),
                'prev_close': float(parts[5]) if len(parts) > 5 else 0,
                'open': float(parts[1]),
                'high': float(parts[6]),
                'low': float(parts[7]),
                'volume': int(float(parts[4])) if len(parts) > 4 else 0,
                'amount': 0,
                'date': parts[10].rstrip('"') if len(parts) > 10 else '',
                'time': parts[0],
                'unit': '美元/盎司',
                'source': 'sina',
                'type': 'gold',
            }
        elif sina_code == 'hf_XAU' and len(parts) >= 13:
            return {
                'name': '伦敦金',
                'price': float(parts[0]),
                'prev_close': float(parts[7]),
                'open': float(parts[3]),
                'high': float(parts[4]),
                'low': float(parts[5]),
                'volume': 0,
                'amount': 0,
                'date': parts[11] if len(parts) > 11 else '',
                'time': parts[6],
                'unit': '人民币/克',
                'source': 'sina',
                'type': 'gold',
            }
        else:
            return {
                'name': SINA_SPECIAL_CODES.get(sina_code, sina_code),
                'price': 0,
                'source': 'sina',
                'type': 'gold',
            }

    # ============ 腾讯 API (备用数据源) ============

    def fetch_tencent_batch(self, codes: list) -> dict:
        """腾讯批量获取实时行情 (含买卖五档)
        返回: {code: {name, price, prev_close, ... bid1-5, ask1-5 ...}}
        """
        all_tencent_codes = []
        for code in codes:
            prefix = get_market_prefix(code)
            all_tencent_codes.append(f"{prefix}{code}")
        
        if not all_tencent_codes:
            return {}
        
        url = f"{TENCENT_QUOTE_URL}{','.join(all_tencent_codes)}"
        try:
            resp = self.session.get(url, timeout=10)
            resp.encoding = 'gb18030'
            results = {}
            
            for line in resp.text.strip().split(';'):
                if '=' not in line or '~' not in line:
                    continue
                var_part = line.split('=')[0]
                val = line.split('=')[1].strip('"')
                if not val or val == '-':
                    continue
                
                parts = val.split('~')
                if len(parts) < 35:
                    continue
                
                try:
                    # 从腾讯代码中提取原代码
                    tc_code = var_part.split('_')[-1] if '_' in var_part else ''
                    original_code = tc_code[2:] if len(tc_code) > 2 else tc_code

                    price = float(parts[3])
                    prev_close = float(parts[4])
                    if price <= 0:
                        continue

                    # 从88字段中提取基本面数据
                    # [38]=换手率 [39]=PE [43]=振幅 [44]=总市值(亿) [45]=流通市值(亿) [46]=PE2 [47]=流通市值2
                    turnover_rate = 0.0
                    pe = 'N/A'
                    total_mv = 0.0
                    circ_mv = 0.0
                    amplitude = 0.0
                    try:
                        if len(parts) > 38 and parts[38]:
                            turnover_rate = float(parts[38])
                    except (ValueError, IndexError):
                        pass
                    try:
                        if len(parts) > 39 and parts[39] and parts[39] != '-':
                            pe_val = float(parts[39])
                            if pe_val > 0:
                                pe = f"{pe_val:.2f}"
                    except (ValueError, IndexError):
                        pass
                    try:
                        if len(parts) > 43 and parts[43] and parts[43] != '-':
                            amplitude = float(parts[43])
                    except (ValueError, IndexError):
                        pass
                    try:
                        if len(parts) > 44 and parts[44] and parts[44] != '-':
                            total_mv = float(parts[44])  # 亿元
                    except (ValueError, IndexError):
                        pass
                    try:
                        if len(parts) > 45 and parts[45] and parts[45] != '-':
                            circ_mv = float(parts[45])  # 亿元
                    except (ValueError, IndexError):
                        pass

                    results[original_code] = {
                        'name': parts[1],
                        'price': price,
                        'prev_close': prev_close,
                        'open': float(parts[5]),
                        'high': float(parts[33]) if len(parts) > 33 else float(parts[6]),
                        'low': float(parts[34]) if len(parts) > 34 else float(parts[7]),
                        'volume': int(float(parts[6])) if len(parts) > 6 else 0,
                        'amount': float(parts[37]) if len(parts) > 37 else 0,
                        'change_pct': float(parts[32]) if len(parts) > 32 else 0,
                        'date': datetime.now().strftime('%Y-%m-%d'),
                        'time': datetime.now().strftime('%H:%M:%S'),
                        'turnover_rate': turnover_rate,
                        'pe': pe,
                        'total_mv': total_mv,
                        'circ_mv': circ_mv,
                        'amplitude': amplitude,
                        # 买卖五档 (腾讯特色)
                        'bid1_price': float(parts[9]) if len(parts) > 9 else 0,
                        'bid1_vol': int(float(parts[10])) if len(parts) > 10 else 0,
                        'bid2_price': float(parts[11]) if len(parts) > 11 else 0,
                        'bid2_vol': int(float(parts[12])) if len(parts) > 12 else 0,
                        'bid3_price': float(parts[13]) if len(parts) > 13 else 0,
                        'bid3_vol': int(float(parts[14])) if len(parts) > 14 else 0,
                        'bid4_price': float(parts[15]) if len(parts) > 15 else 0,
                        'bid4_vol': int(float(parts[16])) if len(parts) > 16 else 0,
                        'bid5_price': float(parts[17]) if len(parts) > 17 else 0,
                        'bid5_vol': int(float(parts[18])) if len(parts) > 18 else 0,
                        'ask1_price': float(parts[19]) if len(parts) > 19 else 0,
                        'ask1_vol': int(float(parts[20])) if len(parts) > 20 else 0,
                        'ask2_price': float(parts[21]) if len(parts) > 21 else 0,
                        'ask2_vol': int(float(parts[22])) if len(parts) > 22 else 0,
                        'ask3_price': float(parts[23]) if len(parts) > 23 else 0,
                        'ask3_vol': int(float(parts[24])) if len(parts) > 24 else 0,
                        'ask4_price': float(parts[25]) if len(parts) > 25 else 0,
                        'ask4_vol': int(float(parts[26])) if len(parts) > 26 else 0,
                        'ask5_price': float(parts[27]) if len(parts) > 27 else 0,
                        'ask5_vol': int(float(parts[28])) if len(parts) > 28 else 0,
                        'market': parts[0],  # 市场标识
                        'source': 'tencent',
                        # 涨跌停（由 prev_close 计算，供合并时防止被 Sina 的同名字段覆盖）
                        'limit_up': round(prev_close * 1.1, 2) if prev_close > 0 else 0,
                        'limit_down': round(prev_close * 0.9, 2) if prev_close > 0 else 0,
                    }
                except (ValueError, IndexError) as e:
                    continue
            
            self._tencent_ok = True
            return results
            
        except Exception as e:
            self._tencent_ok = False
            print(f"腾讯API失败: {e}")
            return {}

    # ============ 同花顺 K线 (技术分析) ============

    def fetch_tjqka_kline(self, code: str, limit: int = 30) -> list:
        """获取同花顺日K线数据
        数据格式: 分号分隔的逗号字符串
        每条: 日期,开盘,最高,最低,收盘,成交量,成交额,换手率,...
        返回: [{date, open, close, high, low, volume, amount}, ...] (按时间升序)
        """
        url = TJQKA_KLINE_URL.replace('{code}', code)
        headers = {
            'Referer': TJQKA_REFERER.replace('{code}', code),
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        }
        try:
            resp = self.session.get(url, headers=headers, timeout=10)
            text = resp.text
            
            # 解析 JSONP
            if '(' in text and ')' in text:
                json_start = text.index('(')
                json_end = text.rindex(')')
                json_str = text[json_start+1:json_end]
                data = json.loads(json_str)
                
                raw_str = data.get('data', '')
                if not raw_str or not isinstance(raw_str, str):
                    return []
                
                # 分号分隔的日K线数据
                klines = []
                entries = raw_str.split(';')
                for entry in entries:
                    entry = entry.strip()
                    if not entry:
                        continue
                    p = entry.split(',')
                    if len(p) >= 7:
                        try:
                            klines.append({
                                'date': p[0],
                                'open': float(p[1]),
                                'high': float(p[2]),
                                'low': float(p[3]),
                                'close': float(p[4]),
                                'volume': float(p[5]),
                                'amount': float(p[6]),
                            })
                        except ValueError:
                            continue
                
                # 返回最近limit条（数据已是按时间升序）
                return klines[-limit:] if len(klines) > limit else klines
            
        except Exception as e:
            print(f"同花顺K线获取失败 {code}: {e}")
            return []
        
        return []

    # ============ 统一接口 ============

    def fetch_realtime(self, codes: list, include_specials: list = None) -> dict:
        """统一实时行情获取 - 自动切换数据源

        数据源策略:
        1. 腾讯 (A股) → 主数据源（88字段，含换手率/PE/市值等）
        2. 新浪 (A股/指数/金银) → 备用
        3. 东方财富 fundgz (ETF) → 补充ETF估值
        """
        results = {}

        # 分离ETF和个股
        etf_codes = [c for c in codes if self.identify_stock_type(c) == 'etf']
        stock_codes = [c for c in codes if self.identify_stock_type(c) != 'etf']

        # 1. 腾讯 (A股/指数 - 88字段，含换手率/PE/市值)
        if stock_codes and self._tencent_ok:
            tencent_data = self.fetch_tencent_batch(stock_codes)
            results.update(tencent_data)

        # 2. 新浪 (补充腾讯缺失的数据)
        if stock_codes and self._sina_ok:
            sina_data = self.fetch_sina_batch(stock_codes, include_specials)
            for code, d in sina_data.items():
                if code not in results:
                    results[code] = d
                else:
                    # 腾讯有数据时：腾讯优先
                    # 仅用 Sina 补充腾讯缺失的关键字段
                    FILL_KEYS = {'turnover_rate', 'open', 'high', 'low', 'name'}
                    for k in FILL_KEYS:
                        if k in d and k not in results[code]:
                            results[code][k] = d[k]

        # 3. 东方财富 fundgz (ETF估值)
        if etf_codes:
            em_etf = self._em_alt.fetch_etf_realtime(etf_codes)
            results.update(em_etf)
            missing_etf = [c for c in etf_codes if c not in em_etf]
            if missing_etf and self._sina_ok:
                sina_data = self.fetch_sina_batch(missing_etf)
                for c, d in sina_data.items():
                    if c not in results:
                        results[c] = d
        
        return results

    def fetch_kline(self, code: str, limit: int = 30) -> list:
        """获取历史K线数据 (用于技术分析)"""
        return self.fetch_tjqka_kline(code, limit)

    def fetch_financial(self, code: str) -> dict:
        """获取基本面数据 (东方财富emweb)"""
        market = self._em_alt.get_market_suffix(code)
        return self._em_alt.fetch_financial_summary(code, market)

    def fetch_company(self, code: str) -> dict:
        """获取公司概况 (东方财富emweb)"""
        market = self._em_alt.get_market_suffix(code)
        return self._em_alt.fetch_company_profile(code, market)

    # ============ 辅助方法 ============

    def identify_stock_type(self, code: str) -> str:
        """识别股票类型"""
        prefix3 = code[:3]
        # ETF前缀
        if prefix3 in ('510', '511', '512', '513', '515', '516', '518', '519', '501', '502', '505', '506', '159', '160'):
            return STOCK_TYPE["ETF"]
        elif code.startswith('XAU') or code.startswith('XAG') or code == 'hf_XAU':
            return STOCK_TYPE["GOLD"]
        else:
            return STOCK_TYPE["INDIVIDUAL"]

    def format_change(self, price: float, prev_close: float) -> tuple:
        """格式化涨跌信息 (红涨绿跌)
        返回: (change_pct, color_emoji, change_text)
        """
        if prev_close <= 0:
            return (0, '⚪', '+0.00%')
        
        change_pct = (price - prev_close) / prev_close * 100
        
        if change_pct > 0:
            color = '🔴'  # 红涨
            sign = '+'
        elif change_pct < 0:
            color = '🟢'  # 绿跌
            sign = ''
        else:
            color = '⚪'
            sign = '+'
        
        return (change_pct, color, f"{sign}{change_pct:.2f}%")


# ============ 兼容层：v1.0 脚本兼容 ============

# 全局单例
_ds_instance = None

def _get_ds():
    global _ds_instance
    if _ds_instance is None:
        _ds_instance = DataSource()
    return _ds_instance

def fetch_stock_data(stock_codes: list, include_specials: list = None) -> dict:
    """兼容 v1.0 的模块级函数：批量获取实时行情"""
    ds = _get_ds()
    raw = ds.fetch_realtime(stock_codes, include_specials)
    results = {}
    for code, d in raw.items():
        price = d.get('price', d.get('current', 0))
        prev_close = d.get('prev_close', 0)
        source = d.get('source', 'unknown')

        # 对于ETF（fundgz数据源），直接使用API返回的change_pct
        if source == 'eastmoney_fundgz':
            change_pct_num = float(d.get('change_pct', 0))
            if change_pct_num > 0:
                sign = '+'
            elif change_pct_num < 0:
                sign = ''
            else:
                sign = '+'
            change_text = f"{sign}{change_pct_num:.2f}%"
        else:
            change_pct_num, _, change_text = ds.format_change(price, prev_close)

        results[code] = {
            'name': d.get('name', code),
            'current': price,
            'prev_close': prev_close,
            'open': d.get('open', 'N/A'),
            'high': d.get('high', 'N/A'),
            'low': d.get('low', 'N/A'),
            'volume': d.get('volume', 0),
            'amount': d.get('amount', 0),
            'change_pct': change_text,
            'change_pct_num': change_pct_num,
            'turnover_rate': d.get('turnover_rate', d.get('turnover', 0)),
            'total_mv': d.get('total_mv', 0),
            'circ_mv': d.get('circ_mv', 0),
            'source': source,
        }
    return results

def fetch_stock_detail(stock_code: str) -> dict:
    """兼容 v1.0 的模块级函数：获取单只股票详情（含买卖五档）"""
    ds = _get_ds()

    # 1. 腾讯获取实时行情（含买卖五档+基本面）
    raw = ds.fetch_tencent_batch([stock_code])
    d = dict(raw.get(stock_code, {})) if raw else {}

    # 2. 补充从realtime（用于获取换手率等 Sina 特有字段）
    try:
        rt = ds.fetch_realtime([stock_code])
        if stock_code in rt:
            for k, v in rt[stock_code].items():
                if k not in d and v not in (None, 0, 0.0, 'N/A', ''):
                    d[k] = v
    except:
        pass

    # 3. 从东方财富获取基本面（PE/BPS）
    bps_val = 0
    pe_ttm_val = 0
    try:
        from eastmoney_alt import EastMoneyAltSource
        em = EastMoneyAltSource()
        market = 'SZ' if stock_code.startswith(('000', '001', '002', '003', '300')) else 'SH'
        fin = em.fetch_financial_summary(stock_code, market)
        if fin:
            bps_val = fin.get('bps', 0)
            pe_ttm_val = fin.get('pe_ttm', 0)
    except:
        pass

    if not d or d.get('price', 0) == 0:
        return None

    price = d.get('price', d.get('current', 0))
    prev_close = d.get('prev_close', 0)
    change_pct_num, _, change_text = ds.format_change(price, prev_close)

    # 涨跌停（腾讯批量已从 prev_close 计算好，直接取用）
    limit_up = d.get('limit_up', 0)
    limit_down = d.get('limit_down', 0)

    # PE: 优先用东方财富的 PE(TTM)，不用腾讯的值（腾讯的PE不准）
    pe_str = 'N/A'
    if pe_ttm_val > 0:
        pe_str = f"{pe_ttm_val:.2f}"

    # PB: 用当前股价 / 每股净资产
    pb_str = d.get('pb', 'N/A')
    if bps_val > 0:
        try:
            pb_val = price / bps_val
            pb_str = f"{pb_val:.2f}"
        except (ValueError, ZeroDivisionError):
            pass

    result = {
        'name': d.get('name', stock_code),
        'current': price,
        'prev_close': prev_close,
        'open': d.get('open', 'N/A'),
        'high': d.get('high', 'N/A'),
        'low': d.get('low', 'N/A'),
        'volume': d.get('volume', 0),
        'amount': d.get('amount', 0),
        'change_pct': change_text,
        'change_pct_num': change_pct_num,
        'turnover_rate': d.get('turnover_rate', 0),
        'total_mv': d.get('total_mv', 0),   # 亿元（腾讯提供）
        'circ_mv': d.get('circ_mv', 0),     # 亿元（腾讯提供，可能为0）
        'pe': pe_str,
        'pb': pb_str,
        'amplitude': d.get('amplitude', 'N/A'),
        'limit_up': limit_up,
        'limit_down': limit_down,
        'source': d.get('source', 'unknown'),
    }
    # 买卖五档
    for i in range(1, 6):
        result[f'bid{i}_price'] = d.get(f'bid{i}_price', 0)
        result[f'bid{i}_vol'] = d.get(f'bid{i}_vol', 0)
        result[f'ask{i}_price'] = d.get(f'ask{i}_price', 0)
        result[f'ask{i}_vol'] = d.get(f'ask{i}_vol', 0)
    return result


# ============ 快速测试 ============

if __name__ == '__main__':
    ds = DataSource()
    
    # 测试1: 实时行情
    print("=== 实时行情测试 ===")
    codes = ['600519', '159892', '518880', '000001']
    specials = ['XAUUSD']
    data = ds.fetch_realtime(codes, specials)
    for code, d in data.items():
        # fundgz 返回的 ETF 数据直接包含 change_pct 字段
        if d.get('source') == 'eastmoney_fundgz':
            change_pct = d.get('change_pct', 0)
            color = '🔴' if change_pct > 0 else '🟢' if change_pct < 0 else '⚪'
            unit = d.get('unit', '元')
            print(f"  {color} {d.get('name', code)} ({code}): {d.get('price', 0):.4f} {unit} ({change_pct:+.2f}%)")
        else:
            change_pct, color, change_text = ds.format_change(d.get('price', 0), d.get('prev_close', 0))
            unit = d.get('unit', '元')
            print(f"  {color} {d.get('name', code)} ({code}): {d.get('price', 0):.4f} {unit} {change_text}")
    
    # 测试2: K线数据
    print("\n=== K线数据测试 ===")
    klines = ds.fetch_kline('600519', 5)
    if klines:
        for k in klines[-5:]:
            print(f"  {k['date']}: 开{k['open']:.2f} 收{k['close']:.2f} 高{k['high']:.2f} 低{k['low']:.2f} 量{k['volume']}")
    else:
        print("  K线数据获取失败")
