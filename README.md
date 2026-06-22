# Stock Watcher 股票盯盯 v2.0

专业股票智能监控系统，支持 A 股、ETF、港股及国际贵金属的实时盯盘、技术分析、风险评估与智能预警。

**数据源架构**：腾讯（主）→ 新浪（备）→ 东方财富 ETF，最大限度保障数据稳定性。

---

## 安装

### 依赖

```bash
pip install requests
```

### 自选股管理命令

```bash
cd scripts

# 添加自选股
python manage.py add 600519  # 沪市
python manage.py add 002600  # 深市
python manage.py add hk00700 # 港股
python manage.py add usAAPL  # 美股

# 查看自选列表
python manage.py list

# 移除自选股
python manage.py remove 600519

# 清空自选列表
python manage.py clear
```

---

## 核心功能速查

| 命令 | 功能 |
|------|------|
| `python manage.py list` | 查看当前自选股列表 |
| `python summarize_performance.py` | 一键生成所有自选股当日行情摘要 |
| `python query_detail.py` | 个股深度分析（技术评分 + 风险提示 + 段永平框架） |
| `python query_stock_detail.py` | 个股 88 字段详细信息（含 PE/PB/ROE/涨停价） |
| `python technical_analysis.py` | 技术指标分析（MACD/KDJ/MA/BOLL） |
| `python stock_analyzer.py --analyze` | 段永平选股框架量化评分 |
| `python stock_analyzer.py --serenity` | Serenity 量化系统瓶颈分析 |
| `python risk_advice.py risk` | 个股风险评估报告 |
| `python risk_advice.py advice` | 基于风险的操盘建议 |
| `python daily_report.py` | 收盘自选股汇总报告 |
| `python monitor.py` | 七大预警实时监控 |
| `python eastmoney_alt.py` | 东方财富辅助工具（ETF/基金数据） |

---

## 行情摘要

```bash
python summarize_performance.py
```

**示例输出：**
```
贵州茅台 (600519)  ¥1215.00  🔴+1.02%  PE=43.68  市值=1.55万亿  换手=0.47%
领益智造 (002600)  ¥16.82    🟢-0.59%  PE=42.31  市值=1199亿   换手=1.85%
恒生ETF (159920)   ¥1.234    ⚪+0.00%  —————
```

---

## 个股深度分析

```bash
python query_detail.py 600519
```

分析内容：综合评分（段永平框架）、技术指标、风险提示、Serenity 瓶颈、操盘建议、PE/PB 估值区间。

---

## 七大预警规则

| 规则 | 说明 | 个股阈值 | ETF 阈值 |
|------|------|---------|---------|
| 成本百分比 | 盈亏提醒 | 自定义 | 自定义 |
| 单日涨跌幅 | 大幅波动 | ±4% | ±2% |
| 成交量异动 | 放量/缩量 | 2倍 | 1.8倍 |
| 均线金叉/死叉 | 趋势判断 | MA5/10/20 | MA5/10/20 |
| RSI 超买超卖 | 超买>70/超卖<30 | 70/30 | 70/30 |
| 跳空缺口 | 向上/向下跳空 | >1% | >0.5% |
| 动态止盈止损 | 移动止损 | 自定义% | 自定义% |

### 预警分级

- 🚨 **紧急级**：≥3 个条件同时触发
- ⚠️ **警告级**：2 个条件触发
- 📢 **提醒级**：1 个条件触发

---

## 配置说明

### 自选股列表文件

自选股数据保存在 `scripts/watchlist.json`，由 `manage.py add/remove/clear` 命令自动维护。

### 预警配置（monitor.py）

编辑 `scripts/monitor.py` 中的 `WATCHLIST`，设置持仓成本和预警阈值：

```python
WATCHLIST = [
    {
        "code": "600519",
        "name": "贵州茅台",
        "market": "sh",
        "type": "individual",   # individual / etf / gold
        "cost": 1600.00,        # 持仓成本（可选）
        "focus": True,
        "alerts": {
            "cost_pct_above": 15.0,   # 盈利 15% 提醒
            "cost_pct_below": -12.0,  # 亏损 12% 止损
            "change_pct_above": 4.0,  # 日内涨 4%
            "change_pct_below": -4.0, # 日内跌 4%
            "volume_surge": 2.0,      # 放量 2 倍
        }
    }
]
```

### 数据源优先级

| 市场 | 主数据源 | 备用 | 说明 |
|------|---------|------|------|
| A股 / 港股 / 美股 | 腾讯财经 | 新浪财经 | 腾讯 88 字段优先，新浪仅补缺 |
| ETF / 基金 | 东方财富 fundgz | 腾讯 | 东方财富 ETF 数据专用接口 |

---

## 交易规则提醒

- **A股主板**：100 股整数倍，最小买入 100 股
- **A股科创板**：200 股整数倍
- **A股创业板**：100 股整数倍
- **ETF / 港股**：无整手限制，按实际数量买卖
- 涨停股票无法买入，跌停股票无法卖出
- **T+1 制度**：当日买入，当日不可卖出

---

## 文件结构

```
stock-watcher/
├── SKILL.md              # OpenClaw 技能配置（必读）
├── README.md             # 本文件
├── skill-card.md         # 功能卡片简介
├── 测试说明.md           # 功能测试说明
├── requirements.txt      # Python 依赖
├── control.sh            # Linux/Mac 后台控制脚本
├── config-example.py     # 配置示例
└── scripts/
    ├── manage.py              # 自选股管理（add/list/remove/clear）
    ├── summarize_performance.py  # 批量行情摘要
    ├── query_detail.py        # 个股深度分析（推荐）
    ├── query_stock_detail.py  # 88字段详细信息
    ├── technical_analysis.py  # 技术指标分析
    ├── stock_analyzer.py      # 段永平评分 + Serenity 分析
    ├── risk_advice.py         # 风险评估 + 操盘建议
    ├── daily_report.py        # 收盘汇总报告
    ├── monitor.py             # 七大预警实时监控
    ├── monitor_stocks.py      # 基础行情监控
    ├── eastmoney_alt.py       # 东方财富辅助工具
    └── watchlist_manager.py   # 自选股底层管理
```

---

## 数据说明

| 字段 | 来源 | 说明 |
|------|------|------|
| 现价/涨跌幅/成交量 | 腾讯/新浪 | 实时行情 |
| 市值/PE/PB/ROE | 腾讯 88 字段 + 东方财富 | 腾讯优先 |
| MACD/KDJ/MA/BOLL | 腾讯历史数据计算 | 盘中近似实时 |
| ETF 涨跌 | 东方财富 fundgz | 专用接口 |
| 涨停/跌停价 | prev_close × 1.1/0.9 | 沪深 10% 规则 |

---

## ⚠️ 注意事项

1. **技术指标有滞后性**：MACD/KDJ 等为滞后指标，用于确认趋势而非预测方向
2. **预警是参考信号**：不是交易指令，不要每个信号都操作
3. **多条件共振更可靠**：多个指标同时触发时胜率更高
4. **段永平评分仅供参考**：量化打分不能替代基本面研究
5. **T+1 规则**：A股当日买入不可当日卖出

**核心原则**：预警系统目标是"不错过大机会，不犯大错误"，不是"抓住每一个波动"。
