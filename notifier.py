import requests
import pandas as pd
import logging
from datetime import datetime
import config

logger = logging.getLogger(__name__)

_URL = "https://sctapi.ftqq.com/{sendkey}.send"

# 各类费用估算
_BUY_COMM  = 0.025  # 场内买入佣金
_SELL_COMM = 0.025  # 场内卖出佣金
_SUB_FEE   = 0.1    # 场外申购费（广发网上折扣后约0.1%）
_REDEEM_FEE = 1.5   # 场外赎回费（持有<7天，最保守估算）


def send(opportunities: pd.DataFrame) -> bool:
    if not config.SENDKEY:
        logger.error("config.py 中 SENDKEY 未填写")
        return False

    max_rate = opportunities['折溢价率'].abs().max()
    title = f"【LOF套利】{len(opportunities)} 个机会 · 最高偏离 {max_rate:.2f}%"
    content = _build_markdown(opportunities)

    try:
        resp = requests.post(
            _URL.format(sendkey=config.SENDKEY),
            data={"title": title, "desp": content},
            timeout=10,
        )
        result = resp.json()
        if result.get("data", {}).get("errno") == 0 or result.get("code") == 200:
            logger.info(f"推送成功: {title}")
            return True
        logger.error(f"Server酱返回错误: {result}")
        return False
    except Exception as e:
        logger.error(f"推送失败: {e}")
        return False


def _calc_net_profit(rate: float) -> float:
    """估算扣除手续费后的净收益率"""
    if rate > 0:  # 溢价套利：申购 + 卖出
        return rate - _SUB_FEE - _SELL_COMM
    else:         # 折价套利：买入 + 赎回
        return abs(rate) - _BUY_COMM - _REDEEM_FEE


def _build_steps(rate: float, code: str, name: str) -> str:
    """生成广发易淘金具体操作步骤"""
    if rate < 0:  # 折价套利
        return (
            f"**折价套利操作步骤（广发易淘金）：**\n\n"
            f"1. 打开广发易淘金 → 底部「交易」→「买入」\n"
            f"2. 搜索代码 `{code}`（{name}），按当前场内价挂单买入\n"
            f"3. 买入成交后 → 底部「理财」→「基金」→「持仓」\n"
            f"4. 找到该基金 → 点「赎回」→ 全部赎回\n"
            f"5. T+1 到T+2 资金到账\n\n"
            f"> ⚠️ **注意**：赎回前务必查看该基金赎回费率。\n"
            f"> 广发APP路径：基金详情页 → 费率说明。\n"
            f"> 若持有不足7天赎回费为1.5%，持有7-30天为0.75%。\n"
            f"> 只有折价幅度能覆盖赎回费时才操作！"
        )
    else:  # 溢价套利
        return (
            f"**溢价套利操作步骤（广发易淘金）：**\n\n"
            f"1. 打开广发易淘金 → 底部「理财」→「基金」\n"
            f"2. 搜索代码 `{code}`（{name}），点「申购」\n"
            f"3. 以当日净值申购，T+1 获得基金份额\n"
            f"4. 份额到账后 → 联系广发客服或在APP内申请「转托管」（场外转场内）\n"
            f"5. 转登记完成后 → 底部「交易」→「卖出」该基金，以溢价价格挂单卖出\n\n"
            f"> ⚠️ **注意**：溢价套利步骤多、耗时2-3天，期间溢价可能收窄。\n"
            f"> 建议溢价超过 **1.5%** 再操作，低于此值风险较大。\n"
            f"> 「转托管」在广发APP：我的 → 客户服务 → 基金转托管"
        )


def _build_markdown(df: pd.DataFrame) -> str:
    now = datetime.now().strftime('%H:%M')
    has_nav = '净值' in df.columns
    blocks = [f"# LOF/ETF 套利机会提醒  {now}\n"]

    for _, r in df.iterrows():
        rate     = r['折溢价率']
        net      = _calc_net_profit(rate)
        tag      = "溢价" if rate > 0 else "折价"
        nav_str  = f"{r['净值']:.4f}" if has_nav and pd.notna(r.get('净值')) else "—"
        steps    = _build_steps(rate, r['代码'], r['名称'])

        profit_line = (
            f"**预估净利润：约 {net:.2f}%**（已扣除手续费）"
            if net > 0
            else f"**预估净利润：{net:.2f}%（手续费后亏损，不建议操作）**"
        )

        blocks.append(
            f"---\n"
            f"### [{tag}] {r['代码']} {r['名称']}\n\n"
            f"| 场内价 | 净值 | 折溢价率 |\n"
            f"|:---:|:---:|:---:|\n"
            f"| {r['场内价']:.3f} | {nav_str} | **{rate:+.2f}%** |\n\n"
            f"{profit_line}\n\n"
            f"{steps}\n"
        )

    return "\n".join(blocks)
