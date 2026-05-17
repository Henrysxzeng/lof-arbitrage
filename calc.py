"""
套利利润计算器 —— 收到通知后，输入基金代码和资金量，估算实际收益。

用法：
    python calc.py 161725 2.8 50000
    参数：基金代码  折价率(%)  投入金额(元)
"""
import sys
from fee_fetcher import get_redemption_fee

BUY_COMM  = 0.025   # 买入佣金 %
MIN_COMM  = 5       # 最低佣金（元），小额交易实际成本更高

def calc(code: str, discount_pct: float, budget: float):
    fee  = get_redemption_fee(code)
    comm = max(budget * BUY_COMM / 100, MIN_COMM)
    comm_pct = comm / budget * 100

    total_cost = comm_pct + fee
    net_profit_pct = discount_pct - total_cost
    net_profit_yuan = budget * net_profit_pct / 100

    # 冲击成本估算（需手动填入日成交额）
    print(f"\n{'='*45}")
    print(f"基金代码    : {code}")
    print(f"折价率      : {discount_pct:.2f}%")
    print(f"投入金额    : {budget:,.0f} 元")
    print(f"{'─'*45}")
    print(f"买入佣金    : {comm_pct:.3f}%  ({comm:.1f} 元)")
    print(f"赎回费(<7天): {fee:.2f}%  ({budget * fee / 100:.1f} 元)")
    print(f"总成本      : {total_cost:.3f}%")
    print(f"{'─'*45}")
    net_str = f"+{net_profit_pct:.2f}%" if net_profit_pct > 0 else f"{net_profit_pct:.2f}%"
    yuan_str = f"+{net_profit_yuan:.0f}" if net_profit_yuan > 0 else f"{net_profit_yuan:.0f}"
    print(f"预期净利润  : {net_str}  ({yuan_str} 元)")
    print(f"{'─'*45}")

    # 冲击成本提示
    print(f"\n冲击成本参考（公式：投入/日成交额 × 1%）：")
    for daily in [50, 100, 200, 500]:
        impact = budget / (daily * 10000) * 1.0
        print(f"  若日成交 {daily}万：冲击约 {impact:.2f}%，"
              f"含冲击净利 {net_profit_pct - impact:.2f}%")

    print(f"\n建议：单笔不超过当日成交额的 10%")
    print(f"{'='*45}\n")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("用法: python calc.py <基金代码> <折价率%> <投入金额元>")
        print("示例: python calc.py 161725 2.8 50000")
        sys.exit(1)
    calc(sys.argv[1], float(sys.argv[2]), float(sys.argv[3]))
