# Stock Watcher Skill v1.0

A simple yet powerful stock monitoring skill for OpenClaw that helps you track A-share stocks in real-time.

## Features

✅ **Real-time Stock Price Query** - Get instant access to real-time A-share stock prices using Sina Finance API  
✅ **Watchlist Management** - Easily add/remove stocks to your personal watchlist  
✅ **Intelligent Monitoring** - Automatically monitor stocks during trading hours and alert on significant price movements  
✅ **No API Key Required** - Uses free, public APIs (Sina Finance) - no registration needed  
✅ **Fast & Reliable** - Response time < 1 second, data delay ~3 seconds  

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
  当前价：¥1215.000  (-2.02%)
  今开：¥1235.000  最高：¥1238.870  最低：¥1211.220
  昨收：¥1240.000
  成交量：574.72万手  成交额：70.17亿
  更新时间：2026-06-18 15:00:03
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

### Data Source

**Primary:** Sina Finance Real-time API  
**Endpoint:** `http://hq.sinajs.cn/list={stock_codes}`  
**Update frequency:** ~3 seconds  
**Cost:** Free, no registration required  

### Supported Markets

- ✅ Shanghai Stock Exchange (SH, codes starting with 6)
- ✅ Shenzhen Stock Exchange (SZ, codes starting with 0 or 3)
- ❌ Hong Kong stocks (not yet supported)
- ❌ US stocks (not yet supported)

### Dependencies

- Python 3.6+
- `requests` (for API calls)
- `beautifulsoup4` (for fallback data parsing)
- `lxml` (XML/HTML parser)

## File Structure

```
stock-watcher/
├── SKILL.md              # Skill definition and metadata
├── README.md             # This file
└── scripts/
    ├── add_stock.py      # Add stock to watchlist
    ├── remove_stock.py   # Remove stock from watchlist
    ├── list_stocks.py    # List all stocks in watchlist
    ├── clear_watchlist.py # Clear entire watchlist
    ├── summarize_performance.py  # View watchlist performance
    ├── monitor_stocks.py          # Real-time monitoring script
    ├── config.py         # Configuration management
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

### v1.0 (2026-06-21)
- ✅ Initial release
- ✅ Real-time price query using Sina Finance API
- ✅ Watchlist management (add/remove/list/clear)
- ✅ Performance summary
- ✅ Intelligent monitoring with alert system
- ✅ Windows command line UTF-8 encoding fix

## Support

For issues and feature requests, please contact the author or submit an issue on the publishing platform.

---

**Author:** OpenClaw User  
**Created:** 2026-06-21  
**Last Updated:** 2026-06-21

