"""比较多只LOF基金的历史折价分布"""
from backtest import fetch_nav, fetch_price
import pandas as pd

FUNDS = [
    # 商品 LOF（这才是专业人士说的"常见套利"来源）
    ("518880", "华安黄金ETF(LOF)"),
    ("161226", "白银LOF"),
    ("501018", "富国石油基金LOF"),
    # A 股指数 LOF（之前测的，机会少）
    ("160706", "嘉实沪深300LOF"),
    ("163407", "兴全趋势LOF"),
]

START, END = "2020-01-01", "2025-12-31"

rows = []
for code, name in FUNDS:
    nav   = fetch_nav(code, START, END)
    price = fetch_price(code, START, END)
    if nav.empty or price.empty:
        print(f"{code} {name}: 数据不足")
        continue
    df = pd.DataFrame({"price": price["close"], "nav": nav["nav"]}).dropna()
    df["d"] = (df["nav"] - df["price"]) / df["nav"] * 100
    rows.append({
        "代码": code, "名称": name,
        "交易日": len(df),
        "最大折价%": round(df["d"].max(), 2),
        "均值%":    round(df["d"].mean(), 3),
        ">1%天":   int((df["d"] > 1).sum()),
        ">2%天":   int((df["d"] > 2).sum()),
        ">2.5%天": int((df["d"] > 2.5).sum()),
    })

print(pd.DataFrame(rows).to_string(index=False))
