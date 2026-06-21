# Stock Watcher Skill v1.0

> A 股行情监控工具，支持双数据源（新浪 + 腾讯）自动切换，无需 API 密钥，提供实时行情、自选股管理与盘中监控告警。

## 功能特色

✅ **实时股价查询** —— 新浪主用 + 腾讯备用，故障时自动整体切换
✅ **自选股管理** —— 添加、删除、查看、清空自选股列表
✅ **盘中智能监控** —— 交易时段自动监控，价格大幅变动时告警
✅ **无需 API 密钥** —— 使用免费公开 API，无需注册
✅ **快速可靠** —— 腾讯 API 响应 ~77ms，整体延迟 < 3 秒

## Features (English)

✅ **Real-time Stock Price Query** - Sina primary + Tencent failover (automatic switch on failure)
✅ **Watchlist Management** - Add, remove, list, or clear your personal stock watchlist
✅ **Intelligent Monitoring** - Auto-monitor during trading hours with price-movement alerts
✅ **No API Key Required** - Uses free, public APIs - no registration needed
✅ **Fast & Reliable** - Tencent API ~77ms response, overall latency < 3 seconds

## Quick Start

### Installation

#### Method 1: Using SkillHub (Recommended)
```bash
skillhub_install install_skill stock-watcher
```

#### Method 2: Manual Installation
1. Copy this skill folder to your OpenClaw skills directory:
   ```bash
   cp -r stock-watcher ~/.qclaw/skills/
   ```

2. Install dependencies:
   ```bash
   cd ~/.qclaw/skills/stock-watcher/scripts
   pip install requests beautifulsoup4 lxml
   ```

### Basic Usage

Once installed, you can interact with the skill through OpenClaw:

**Add stocks to watchlist:**
```
添加自选 600519
添加自选 002600 领益智造
```

**View watchlist:**
```
查看自选股行情
```

**Remove from watchlist:**
```
删除自选 600519
```

**Clear watchlist:**
```
清空自选股
```

## Advanced Features

### Real-time Price Query

The skill uses Sina Finance's real-time API to fetch stock prices. No API key or registration required.

**Example output:**
```
【贵州茅台】(SH600519)
  当前价:¥1215.000  (-2.02%)
  今开:¥1235.000  最高:¥1238.870  最低:¥1211.220
  昨收:¥1240.000
  成交量:574.72万手  成交额:70.17亿
  更新时间:2026-06-18 15:00:03
```

### Intelligent Monitoring (New in v1.0)

The `monitor_stocks.py` script can be used with cron jobs to automatically monitor your watchlist during trading hours:

**Configuration file:** `~/.openclaw/stock_watcher/monitor_config.json`

**Example configuration:**
```json
{
  "change_threshold": 5.0,
  "price_alerts": {
    "002600": {"high": 17.0, "low": 15.0},
    "600601": {"high": 15.0, "low": 14.0}
  },
  "volume_surge_ratio": 2.0
}
```

**Monitoring triggers:**
- Price change ≥ `change_threshold`%
- Price reaches target price (`high`)
- Price falls to stop-loss price (`low`)

**Integration with OpenClaw Cron:**
Create a cron job to run `monitor_stocks.py` every 5 minutes during trading hours (Monday-Friday 09:30-15:00).

## Technical Details

### Data Source (Dual API)

| API | Endpoint | Latency | Fields | Level 2 |
|-----|----------|---------|--------|---------|
| **Sina Finance** (Primary) | `hq.sinajs.cn` | ~107ms | 34 | ❌ |
| **Tencent Finance** (Failover) | `qt.gtimg.cn` | ~77ms | 88 | ✅ |

**Strategy:** Try Sina first; on any failure, **switch entirely to Tencent** (no mixing). Both are free and require no API key.
**Update frequency:** ~3 seconds
**Cost:** Free, no registration required

### Supported Markets

- ✅ 沪市主板（600/601/603/605）
- ✅ 深市主板（000/001/002）
- ✅ 创业板（300）
- ✅ 科创板（688/689）
- ✅ 北交所（430/830/871/873 等）
- ❌ 港股（Tencent API 已支持，待扩展）
- ❌ 美股（待支持）

### Dependencies

- Python 3.6+
- `requests` (for API calls)
- `beautifulsoup4` (for fallback data parsing)
- `lxml` (XML/HTML parser)

## File Structure

```
stock-watcher/
├── SKILL.md              # Skill definition (bilingual CN/EN)
├── README.md             # This file
├── skill-card.md         # ClawHub metadata card
└── scripts/
    ├── add_stock.py      # Add stock to watchlist
    ├── remove_stock.py   # Remove stock from watchlist
    ├── list_stocks.py    # List all stocks in watchlist
    ├── clear_watchlist.py # Clear entire watchlist
    ├── summarize_performance.py  # Watchlist performance summary (dual API)
    ├── monitor_stocks.py          # Real-time monitoring script
    ├── query_stock_detail.py     # 88-field stock detail query (Tencent)
    ├── config.py         # Configuration management
    ├── test_tencent_simple.py    # Tencent API quick test
    ├── install.sh        # Installation script (Linux/macOS)
    └── uninstall.sh      # Uninstallation script (Linux/macOS)
```

## Troubleshooting

### "行情数据暂不可用" (Market data temporarily unavailable)
**Cause:** Market is closed (weekends, holidays, or outside trading hours)
**Solution:** Wait for market to open (Monday-Friday 09:30-15:00 Beijing time)

### "获取数据失败" (Failed to fetch data)
**Cause:** Network issue or Sina API rate limiting
**Solution:** Wait a few seconds and retry, or check network connection

### Windows command line Chinese character garbled
**Cause:** Windows command line uses GBK encoding by default
**Solution:** The scripts include UTF-8 encoding fixes, make sure you're using Python 3.7+

## Publishing

This skill is ready to be published to:
- OpenClaw SkillHub
- GitHub
- Other OpenClaw skill repositories

**Before publishing:**
1. Update version number in `SKILL.md`
2. Test all scripts on a clean environment
3. Update this README with any new features
4. Create a zip package (without cache files)

## License

MIT License - feel free to modify and distribute.

## Changelog

### v1.0 (2026-06-21) — 本版本
- ✅ 双数据源架构：新浪主用 + 腾讯备用，整体切换逻辑
- ✅ 通用股票详情查询：88 字段完整数据，含 Level 2 买卖五档
- ✅ Windows 中文编码修复：所有脚本强制 UTF-8 无 BOM
- ✅ 版本号统一：所有脚本版本号均为 v1.0
- ✅ 10 个功能脚本全量通过测试

### v0.x — 基于原版 (Robin797860 / ClawHub)
- ✅ 新浪金融 API 实时行情
- ✅ 自选股管理（添加/删除/查看/清空）
- ✅ 性能汇总摘要
- ✅ 盘中智能监控告警

## Support

For issues and feature requests, please contact the author or submit an issue on the publishing platform.

---

**Author:** OpenClaw User
**Created:** 2026-06-21
**Last Updated:** 2026-06-21

