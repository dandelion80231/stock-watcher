#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stock Watcher v3.0 - 集中配置管理
统一管理路径、数据源、监控参数等配置

数据源策略（基于实际测试结果）:
- 东方财富 push2/push2his API: 服务器主动断开连接，不可用 → 放弃
- 新浪财经 API: 稳定可用，支持 A股/ETF/黄金ETF/指数/国际金银 ✅
- 腾讯财经 API: 稳定可用，支持 A股/ETF/指数/港股 ✅
- 同花顺 API: 可用，数据丰富但格式需 JSONP 解析

优先级: sina(实时轻量) > tencent(数据丰富) > tjqka(K线历史)
"""
import os
import json

# ============ 路径配置 ============
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.data')
DATA_DIR = os.path.abspath(DATA_DIR)
os.makedirs(DATA_DIR, exist_ok=True)

WATCHLIST_FILE = os.path.join(DATA_DIR, "watchlist.txt")
PORTFOLIO_FILE = os.path.join(DATA_DIR, "portfolio.json")
MONITOR_CONFIG_FILE = os.path.join(DATA_DIR, "monitor_config.json")
ALERT_LOG_FILE = os.path.join(DATA_DIR, "alert_log.json")
TRADER_DB_FILE = os.path.join(DATA_DIR, "trader_patterns.db")
CACHE_DIR = os.path.join(DATA_DIR, "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

# ============ 数据源优先级 (实际可用) ============
DATA_SOURCE_PRIORITY = ["sina", "tencent", "tjqka"]

# ============ API 配置 ============
# 新浪财经 (主数据源 - 实时轻量)
SINA_QUOTE_URL = "https://hq.sinajs.cn/list="
SINA_REFERER = "https://finance.sina.com.cn"

# 腾讯财经 (备用 - 数据更丰富含买卖五档)
TENCENT_QUOTE_URL = "https://qt.gtimg.cn/q="

# 同花顺 (K线历史数据 - 技术分析用)
TJQKA_KLINE_URL = "http://d.10jqka.com.cn/v6/line/hs_{code}/01/last.js"
TJQKA_REFERER = "http://stockpage.10jqka.com.cn/{code}/"

# ============ 标的类型定义 ============
STOCK_TYPE = {
    "INDIVIDUAL": "individual",   # 个股
    "ETF": "etf",                 # ETF基金
    "GOLD": "gold",               # 黄金/贵金属
    "INDEX": "index",             # 指数
    "HK": "hk",                   # 港股
}

# 标的类型差异化阈值
TYPE_THRESHOLDS = {
    "individual": {
        "change_pct_default": 4.0,    # 日内异动阈值 ±4%
        "volume_surge_default": 3.0,  # 成交量放大倍数
        "rsi_overbought": 70,
        "rsi_oversold": 30,
    },
    "etf": {
        "change_pct_default": 2.0,    # ETF波动小 ±2%
        "volume_surge_default": 1.8,
        "rsi_overbought": 75,
        "rsi_oversold": 25,
    },
    "gold": {
        "change_pct_default": 2.5,    # 黄金 ±2.5%
        "volume_surge_default": None,  # 黄金无量
        "rsi_overbought": 75,
        "rsi_oversold": 25,
    },
}

# ============ 监控默认参数 ============
DEFAULT_MONITOR_CONFIG = {
    "change_threshold": 5.0,
    "volume_surge_ratio": 2.0,
    "check_interval_seconds": 60,
    "alert_cooldown_minutes": 30,   # 同类预警冷却时间
}

# ============ 技术分析参数 ============
TA_MA_PERIODS = [5, 10, 20, 60]
TA_RSI_PERIOD = 14
TA_MACD_FAST = 12
TA_MACD_SLOW = 26
TA_MACD_SIGNAL = 9
TA_BOLL_PERIOD = 20
TA_BOLL_STD = 2.0

# ============ 市场代码映射 ============
# 新浪/腾讯 API 的市场前缀
MARKET_PREFIX_MAP = {
    # 沪市 → sh
    **{p: 'sh' for p in ['600', '601', '603', '688', '689']},
    # 沪市ETF → sh (510/511/512/513/515/516/518/519/501/502/505/506)
    **{p: 'sh' for p in ['510', '511', '512', '513', '515', '516', '518', '519', '501', '502', '505', '506']},
    # 深市 → sz
    **{p: 'sz' for p in ['000', '001', '002', '003', '300']},
    # 深市ETF → sz (159/160)
    **{p: 'sz' for p in ['159', '160']},
    # 北交所 → bj
    **{p: 'bj' for p in ['430', '830', '831', '832', '833', '834', '835', '836', '837', '838', '839', '870', '871', '872', '873']},
}

def get_market_prefix(stock_code: str) -> str:
    """根据股票代码返回市场前缀 (sh/sz/bj)"""
    prefix3 = stock_code[:3]
    return MARKET_PREFIX_MAP.get(prefix3, 'sz')

def get_sina_code(stock_code: str) -> str:
    """生成新浪格式的股票代码 (如 sh600519)"""
    return f"{get_market_prefix(stock_code)}{stock_code}"

def get_tencent_code(stock_code: str) -> str:
    """生成腾讯格式的股票代码 (如 sh600519)"""
    return f"{get_market_prefix(stock_code)}{stock_code}"

# ============ 新浪特殊品种代码 ============
# 国际金银 (新浪外汇接口, XAUUSD 美元/盎司)
SINA_SPECIAL_CODES = {
    "XAUUSD": "国际金价(美元/盎司)",
    "XAGUSD": "国际银价(美元/盎司)",
    "hf_XAU": "伦敦金(人民币/克)",
}

# ============ 工具函数 ============
def load_json(filepath: str, default=None):
    """安全加载 JSON 文件"""
    if not os.path.exists(filepath):
        return default if default is not None else {}
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return default if default is not None else {}

def save_json(filepath: str, data):
    """安全保存 JSON 文件"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_watchlist():
    """加载自选股列表 (格式: code|name 或 code)"""
    if not os.path.exists(WATCHLIST_FILE):
        return []
    stocks = []
    with open(WATCHLIST_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '|' in line:
                code, name = line.split('|', 1)
            else:
                code = line
                name = ''
            stocks.append({"code": code.strip(), "name": name.strip()})
    return stocks

def save_watchlist(stocks):
    """保存自选股列表"""
    with open(WATCHLIST_FILE, 'w', encoding='utf-8') as f:
        for s in stocks:
            f.write(f"{s['code']}|{s['name']}\n")

def load_portfolio():
    """加载持仓配置 (含成本价、预警规则)"""
    return load_json(PORTFOLIO_FILE, {})

def save_portfolio(portfolio):
    """保存持仓配置"""
    save_json(PORTFOLIO_FILE, portfolio)
