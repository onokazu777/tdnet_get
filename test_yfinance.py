# -*- coding: utf-8 -*-
"""yfinance で日本株の PBR/PER が取得できるかテスト"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import yfinance as yf

# テスト銘柄
codes = ['7203', '9143', '8562', '4503', '6758']  # トヨタ, SG HD, 福島銀, アステラス, ソニー

for code in codes:
    ticker = yf.Ticker(f"{code}.T")
    info = ticker.info
    print(f"\n=== {code} ({info.get('shortName', 'N/A')}) ===")
    print(f"  currentPrice:  {info.get('currentPrice')}")
    print(f"  forwardPE:     {info.get('forwardPE')}")
    print(f"  trailingPE:    {info.get('trailingPE')}")
    print(f"  priceToBook:   {info.get('priceToBook')}")
    print(f"  dividendYield: {info.get('dividendYield')}")
    print(f"  marketCap:     {info.get('marketCap')}")
    print(f"  sector:        {info.get('sector')}")
