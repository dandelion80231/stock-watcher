#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stock Watcher v2.0 - 东方财富数据源补充模块
当前网络下 push2.eastmoney.com 不通，但以下接口可用：

1. fundgz.1234567.com.cn - ETF实时估值 ✅ (返回: 估值/涨跌幅/净值)
2. emweb.securities.eastmoney.com - 基本面数据 ✅ (返回: 财报/ROE/毛利率/公司概况)
3. push2.eastmoney.com - 实时行情 ❌ (服务器断开连接)
"""
import sys
import io
if not isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import requests
import json
import re
from datetime import datetime


class EastMoneyAltSource:
    """东方财富备用数据源 (push2不通时的替代方案)"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        })

    # ============ ETF实时估值 (fundgz) ============

    def fetch_etf_realtime(self, codes: list) -> dict:
        """获取ETF实时估值 (fundgz.1234567.com.cn)
        codes: ETF代码列表 ['518880', '159892', '510300']
        返回: {code: {name, price, nav, change_pct, update_time}}
        """
        results = {}
        for code in codes:
            url = f"https://fundgz.1234567.com.cn/js/{code}.js"
            try:
                resp = self.session.get(url, timeout=10)
                if resp.status_code != 200:
                    continue
                
                # 解析 JSONP: jsonpgz({...})
                text = resp.text
                m = re.search(r'jsonpgz\((.+?)\)', text)
                if not m:
                    continue
                
                data = json.loads(m.group(1))
                results[code] = {
                    'name': data.get('name', ''),
                    'price': float(data.get('gsz', 0)),       # 盘中估值
                    'nav': float(data.get('dwjz', 0)),        # 单位净值
                    'prev_nav': float(data.get('dwjz', 0)),   # 昨日净值(用作prev_close近似)
                    'change_pct': float(data.get('gszzl', 0)), # 估值涨跌幅
                    'update_time': data.get('gztime', ''),
                    'source': 'eastmoney_fundgz',
                    'type': 'etf',
                }
            except Exception as e:
                continue
        
        return results

    # ============ 基本面数据 (emweb) ============

    def fetch_financial_summary(self, code: str, market: str = 'SH') -> dict:
        """获取个股财务摘要 (emweb.securities.eastmoney.com)
        返回: {name, roe, eps, net_profit_growth, revenue_growth, gross_margin, pe, ...}
        """
        secucode = f"{code}.{market}"
        url = f"https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/ZYZBAjaxNew?type=0&code={secucode}"
        
        try:
            resp = self.session.get(url, timeout=15)
            if resp.status_code != 200:
                return {}
            
            data = json.loads(resp.text)
            items = data.get('data', [])
            if not items:
                return {}
            
            # 取最近一期数据
            latest = items[0]
            
            return {
                'name': latest.get('SECURITY_NAME_ABBR', ''),
                'report_date': latest.get('REPORT_DATE', ''),
                'report_type': latest.get('REPORT_DATE_NAME', ''),
                'eps': latest.get('EPSJB', 0),                    # 每股收益
                'bps': latest.get('BPS', 0),                       # 每股净资产
                'roe': latest.get('ROEJQ', 0),                     # ROE(加权)
                'net_profit': latest.get('PARENTNETPROFIT', 0),    # 净利润
                'revenue': latest.get('TOTALOPERATEREVE', 0),      # 营业收入
                'net_profit_growth': latest.get('PARENTNETPROFITTZ', 0),  # 净利润增长率%
                'revenue_growth': latest.get('TOTALOPERATEREVETZ', 0),     # 营收增长率%
                'gross_margin': latest.get('XSMLL', 0),            # 销售毛利率%
                'net_margin': latest.get('XSJLL', 0),              # 销售净利率%
                'asset_liability_ratio': latest.get('ZCFZL', 0),   # 资产负债率%
                'current_ratio': latest.get('LD', 0),              # 流动比率
                'cash_ratio': latest.get('XJLLB', 0),              # 现金流量比率
                'pe_ttm': latest.get('PER_TOI', 0),                # PE(TTM)
                'source': 'eastmoney_emweb',
            }
        except Exception as e:
            print(f"基本面数据获取失败 {code}: {e}")
            return {}

    def fetch_pe_pb(self, code: str, market: str = 'SH') -> dict:
        """获取市盈率、市净率等估值指标（用于兼容层）
        返回: {pe, pb, pe_ttm, bps}
        pe = 市盈率(动)，pb = 市净率
        """
        fin = self.fetch_financial_summary(code, market)
        if not fin:
            return {'pe': 'N/A', 'pb': 'N/A', 'pe_ttm': 0, 'bps': 0}
        bps = fin.get('bps', 0)
        pe_ttm = fin.get('pe_ttm', 0)
        # PE(动): 用 PE_TTM 近似
        pe_val = 'N/A'
        if pe_ttm and pe_ttm > 0:
            pe_val = f"{pe_ttm:.2f}"
        # PB: price / bps（需要当前价，这里用腾讯/新浪的实时价估算，在调用前已传入price）
        return {
            'pe': pe_val,
            'pb': 'N/A',  # 待合并时用 price/bps 计算
            'pe_ttm': pe_ttm,
            'bps': bps,
            'source': 'eastmoney_emweb',
        }

    def fetch_company_profile(self, code: str, market: str = 'SH') -> dict:
        """获取公司概况"""
        secucode = f"{code}.{market}"
        url = f"https://emweb.securities.eastmoney.com/PC_HSF10/CompanySurvey/PageAjax?code={secucode}"
        
        try:
            resp = self.session.get(url, timeout=15)
            if resp.status_code != 200:
                return {}
            
            data = json.loads(resp.text)
            jbzl = data.get('jbzl', [])
            if not jbzl:
                return {}
            
            info = jbzl[0]
            return {
                'name': info.get('SECURITY_NAME_ABBR', ''),
                'full_name': info.get('ORG_NAME', ''),
                'industry': info.get('EM2016', ''),               # 行业分类
                'market': info.get('TRADE_MARKET', ''),           # 交易市场
                'chairman': info.get('CHAIRMAN', ''),
                'president': info.get('PRESIDENT', ''),
                'employees': info.get('EMP_NUM', 0),
                'website': info.get('ORG_WEB', ''),
                'address': info.get('ADDRESS', ''),
                'profile': info.get('ORG_PROFILE', ''),
                'source': 'eastmoney_emweb',
            }
        except Exception as e:
            return {}

    # ============ 辅助 ============

    def get_market_suffix(self, code: str) -> str:
        """东方财富 emweb 的市场后缀"""
        prefix3 = code[:3]
        if prefix3 in ('600', '601', '603', '688', '689', '510', '511', '512', '513', '515', '516', '518', '519', '501', '502'):
            return 'SH'
        else:
            return 'SZ'


if __name__ == '__main__':
    em = EastMoneyAltSource()
    
    # 测试1: ETF实时估值
    print("=== ETF实时估值 ===")
    etfs = ['518880', '159892', '510300', '512880']
    data = em.fetch_etf_realtime(etfs)
    for code, d in data.items():
        print(f"  {d['name']} ({code}): 估值={d['price']} 涨跌={d['change_pct']}% 净值={d['nav']} 更新={d['update_time']}")
    
    # 测试2: 基本面数据
    print("\n=== 基本面数据 (600519) ===")
    fin = em.fetch_financial_summary('600519')
    if fin:
        print(f"  {fin['name']} ({fin['report_date']})")
        print(f"  ROE: {fin['roe']}%")
        print(f"  EPS: {fin['eps']}")
        print(f"  净利润增长: {fin['net_profit_growth']}%")
        print(f"  营收增长: {fin['revenue_growth']}%")
        print(f"  毛利率: {fin['gross_margin']}%")
        print(f"  PE(TTM): {fin['pe_ttm']}")
    
    # 测试3: 公司概况
    print("\n=== 公司概况 (600519) ===")
    profile = em.fetch_company_profile('600519')
    if profile:
        print(f"  {profile['name']}: {profile['industry']}")
        print(f"  董事长: {profile['chairman']} 员工: {profile['employees']}")
