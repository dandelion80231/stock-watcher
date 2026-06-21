#!/usr/bin/env python3
"""
Clear the entire watchlist.
This script removes all stocks from the watchlist file.
"""
import os
import sys

# Fix Windows command line UTF-8 encoding
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except:
    pass

# Add script directory to Python path to import config
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import WATCHLIST_FILE

def clear_watchlist():
    """Clear the entire watchlist."""
    # Ensure the directory exists
    os.makedirs(os.path.dirname(WATCHLIST_FILE), exist_ok=True)
    
    # Clear the file by opening in write mode and closing immediately
    with open(WATCHLIST_FILE, 'w', encoding='utf-8') as f:
        pass
    
    print("Watchlist cleared successfully.")

if __name__ == "__main__":
    clear_watchlist()