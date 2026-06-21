---
name: stock-watcher
description: Manage and monitor a personal stock watchlist with support for adding, removing, listing stocks, and summarizing their recent performance using dual API sources (Sina + Tencent). Use when the user wants to track specific stocks, get performance summaries, or manage their watchlist.
---

# Stock Watcher Skill

自选股管理与行情监控工具，支持双数据源（新浪 + 腾讯）自动切换，提供实时行情摘要和详细股票信息查询。

## 功能概览

- ✅ **自选股管理**：添加、删除、查看、清空自选股列表
- ✅ **行情摘要**：实时获取所有自选股的价格、涨跌幅、成交量等关键数据
- ✅ **详细查询**：单只股票 88 字段完整数据（含 Level 2 买卖五档）
- ✅ **双数据源**：新浪主用、腾讯备用，自动切换，数据可靠

## 快速开始

### 添加股票
```
python scripts/add_stock.py 600519
```

### 查看自选股列表
```
python scripts/list_stocks.py
```

### 查看行情摘要
```
python scripts/summarize_performance.py
```

### 查询单只股票详情（88字段）
```
python scripts/query_stock_detail.py 600519
```

### 删除股票
```
python scripts/remove_stock.py 600519
```

### 清空自选股
```
python scripts/clear_watchlist.py
```

---

## 脚本说明

| 脚本 | 功能 | 示例 |
|------|------|------|
| `add_stock.py` | 添加股票到自选股 | `python add_stock.py 600519` |
| `remove_stock.py` | 从自选股删除股票 | `python remove_stock.py 600519` |
| `list_stocks.py` | 列出所有自选股 | `python list_stocks.py` |
| `clear_watchlist.py` | 清空自选股列表 | `python clear_watchlist.py` |
| `summarize_performance.py` | 获取行情摘要（双API） | `python summarize_performance.py` |
| `monitor_stocks.py` | 监控股票价格变动 | `python monitor_stocks.py` |
| `query_stock_detail.py` | 查询股票详情（88字段） | `python query_stock_detail.py 600519` |

---

## 双数据源架构

### 数据源对比

| 特性 | 新浪财经 API | 腾讯财经 API |
|------|-------------|-------------|
| **延迟** | ~107 ms | ~77 ms ✅ |
| **数据字段** | 34 | 88 ✅ |
| **Level 2 买卖五档** | ❌ | ✅ |
| **稳定性** | ✅ 非常稳定 | ✅ 稳定 |

### 自动切换逻辑

1. **优先使用新浪 API**（快速、轻量、稳定）
2. **新浪失败时整体切换到腾讯 API**（数据更丰富，含 Level 2）
3. **不混合两个 API 的数据**（保证数据一致性）

输出示例：
```
贵州茅台 (600519)
  当前价: ¥1215.000  (-2.02%)
  [数据源: sina]

# 或新浪失败时：
贵州茅台 (600519)
  当前价: ¥1215.00  (-2.02%)
  [数据源: tencent]
```

---

## 股票详情查询（88字段）

使用腾讯财经 API 获取完整数据，包括：

**行情数据**
- 当前价、昨收、今开、最高、最低、涨跌幅、涨跌额

**交易数据**
- 成交量、成交额、换手率

**市值数据**
- 总市值、流通市值、总股本

**涨跌停数据**
- 振幅、涨停价、跌停价

**技术指标**
- 市盈率(动态)、市净率

**Level 2 买卖五档**
- 买一~买五（价格 + 手数）
- 卖一~卖五（价格 + 手数）

**支持的股票类型**
- 沪市主板：600/601/603
- 深市主板：000/001/002/003
- 创业板：300
- 科创板：688/689
- 北交所：430/830/871/873 等

**输出示例**
```
======================================================================
股票名称: 中化国际
股票代码: 600500
======================================================================

【行情数据】
  当前价:   ¥8.83
  昨收:     ¥9.20
  涨跌幅:   -4.02%

【交易数据】
  成交量:   4085814 手
  成交额:   356213 万元
  换手率:   11.39%

【市值数据】
  总市值:   316.85 亿元
  流通市值: 316.85 亿元

【买卖五档】
  买一: ¥8.83 (127手)
  卖一: ¥8.84 (177手)

【更新时间】
  2026-06-18 16:14:01
======================================================================
```

---

## 数据存储

自选股存储在：`~/.clawdbot/stock_watcher/watchlist.txt`

格式：
```
600519|贵州茅台
002600|领益智造
```

---

## 注意事项

- **股票代码格式**：6位数字（如 600519）
- **数据延迟**：行情可能有1-3分钟延迟
- **网络依赖**：需要网络连接获取实时数据
- **市场范围**：主要支持A股市场（沪深京）

---

## 安装位置

- **安装目录**：`~/.qclaw/skills/stock-watcher/`
- **桌面备份**：`D:\电脑桌面\stock-watcher-v1.0\`

---

**Version**: v1.0  
**Last Updated**: 2026-06-21

