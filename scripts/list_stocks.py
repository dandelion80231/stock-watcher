#!/usr/bin/env python3
"""
List all stocks in the user's watchlist.
This script reads from the standard watchlist file and displays the current watchlist.
"""
import sys
import os

# Add script directory to Python path to import config
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import WATCHLIST_FILE

def list_stocks():
    """List all stocks in the watchlist."""
    # Fix Windows command line UTF-8 encoding
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass
    
    if not os.path.exists(WATCHLIST_FILE):
        print("Watchlist is empty.")
        return
    
    with open(WATCHLIST_FILE, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f if line.strip()]
    
    if not lines:
        print("Watchlist is empty.")
        return
    
    print("Your Stock Watchlist:")
    print("-" * 40)
    for i, line in enumerate(lines, 1):
        parts = line.split('|')
        if len(parts) == 2:
            code, name = parts
            print(f"{i}. {code} - {name}")
        else:
            print(f"{i}. {line}")

if __name__ == "__main__":
    list_stocks()