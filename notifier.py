from __future__ import annotations
import requests
import pandas as pd
import logging
from datetime import datetime
import config

logger = logging.getLogger(__name__)

_URL = "https://sctapi.ftqq.com/{sendkey}.send"
_BUY_COMM   = 0.025
_SELL_COMM  = 0.025
_SUB_FEE    = 0.1
_REDEEM_FEE = 1.5   # 最保守估算（持有 <7 天）


def _post(title: str, content: str) -> bool:
    if not config.SENDKEY:
        logger.error("SENDKEY 未填写")
        return False
    try:
        resp = requests.post(
            _URL.format(sendkey=config.SENDKEY),
            data={"title": title, "desp": content},
            timeout=10,
        )
        r = resp.json()
        ok = r.get("data", {}).get("errno") == 0 or r.get("code") == 200
        if ok:
            logger.info(f"推送成功: {title}")
        else:
            logger.error(f"推送失败: {r}")
        return ok
    except Exception as e:
        logger.error(f"推送异常: {e}")
        return False


def _net_profit(rate: float) -> float:
    if rate > 0:
        return rate - _SUB_FEE - _SELL_COMM
    return abs(rate) - _BUY_COMM - _REDEEM_FEE


# ── 买入推送 ──────────────────────────────────────────────

def send(opportunities: pd.DataFrame, indices: dict = None, risk: tuple = None) -> bool:
    max_rate = opportunities["折溢价率"].abs().max()
    title = f"【LOF套利】{len(opportunities)} 个机会 · 偏离 {max_rate:.2f}%"
    content = _build_buy_md(opportunities, indices or {}, risk or ("未知", ""))
    return _post(title, content)


def _build_buy_md(df: pd.DataFrame, indices: dict, risk: tuple) -> str:
    now = datetime.now().strftime("%H:%M")
    risk_level, risk_desc = risk
    has_nav = "净值" in df.columns

    # 大盘区块
    if indices:
        idx_lines = "  ".join(
            f"{v['name']} {v['price']} ({v['change_pct']:+.2f}%)"
            for v in indices.values()
        )
    else:
        idx_lines = "数据获取失败"

    blocks = [
        f"# LOF/ETF 套利提醒  {now}",
        "",
        f"**大盘：** {idx_lines}",
        f"**风险评估：** {risk_level} — {risk_desc}",
        "",
    ]

    for _, r in df.iterrows():
        rate    = r["折溢价率"]
        net     = _net_profit(rate)
        tag     = "溢价" if rate > 0 else "折价"
        nav_str = f"{r['净值']:.4f}" if has_nav and pd.notna(r.get("净值")) else "—"
        profit_hint = f"约 **{net:.2f}%**" if net > 0 else f"**{net:.2f}%（手续费后亏损，不建议）**"

        steps = _steps(rate, r["代码"], r["名称"])
        ai_prompt = _ai_prompt(r, rate, net, indices, risk_level, risk_desc)

        blocks += [
            "---",
            f"### [{tag}] {r['代码']} {r['名称']}",
            "",
            f"| 场内价 | 净值 | 折溢价率 | 扣费后净利 |",
            f"|:---:|:---:|:---:|:---:|",
            f"| {r['场内价']:.3f} | {nav_str} | **{rate:+.2f}%** | {profit_hint} |",
            "",
            steps,
            "",
            "> **复制下方指令发给 AI，获取买入建议：**",
            "",
            "```",
            ai_prompt,
            "```",
            "",
        ]

    return "\n".join(blocks)


def _steps(rate: float, code: str, name: str) -> str:
    if rate < 0:
        return (
            f"**操作步骤（广发易淘金）：**\n\n"
            f"1. 交易 → 买入 → 搜索 `{code}` → 限价委托买入\n"
            f"2. 次日：理财 → 场内基金 → 找到 {name} → 赎回\n\n"
            f"> 注意：赎回费率请在基金详情页「费率说明」确认"
        )
    return (
        f"**操作步骤（广发易淘金）：**\n\n"
        f"1. 理财 → 基金 → 搜索 `{code}` → 申购\n"
        f"2. T+1 份额到账后：申请「转托管」（场外转场内）\n"
        f"3. 转托管完成后：交易 → 卖出 `{code}`\n\n"
        f"> 溢价套利步骤多，建议溢价 >1.5% 再操作"
    )


def _ai_prompt(r, rate: float, net: float, indices: dict, risk_level: str, risk_desc: str) -> str:
    tag = "折价" if rate < 0 else "溢价"
    op  = "买入场内，次日赎回" if rate < 0 else "场外申购，次日卖出"
    idx_str = "  ".join(
        f"{v['name']}{v['change_pct']:+.2f}%"
        for v in indices.values()
    ) if indices else "数据不可用"

    return (
        f"我发现一个LOF基金{tag}套利机会，请帮我判断是否值得操作。\n\n"
        f"【机会信息】\n"
        f"基金：{r['名称']}（{r['代码']}）\n"
        f"操作方式：{op}\n"
        f"场内价：{r['场内价']:.3f}  净值：{r.get('净值', '未知')}\n"
        f"折溢价率：{rate:+.2f}%\n"
        f"扣除手续费后预估净利润：{net:.2f}%\n\n"
        f"【今日大盘】\n"
        f"{idx_str}\n"
        f"市场风险评估：{risk_level}（{risk_desc}）\n\n"
        f"【请明确回答以下三点，不要模糊表述】\n"
        f"1. 买还是不买？（只回答【买】或【不买】）\n"
        f"2. 建议投入金额？（给具体数字或比例）\n"
        f"3. 理由（一句话，20字内）"
    )


# ── 次日卖出推送 ──────────────────────────────────────────

def send_followup(items: list, indices: dict = None) -> bool:
    if not items:
        return False
    title = f"【LOF套利·昨日持仓】{len(items)} 只，查看今日操作建议"
    content = _build_followup_md(items, indices or {})
    return _post(title, content)


def _build_followup_md(items: list, indices: dict) -> str:
    now = datetime.now().strftime("%H:%M")
    if indices:
        idx_lines = "  ".join(
            f"{v['name']} ({v['change_pct']:+.2f}%)"
            for v in indices.values()
        )
    else:
        idx_lines = "数据不可用"

    blocks = [
        f"# 昨日套利持仓 · 今日操作建议  {now}",
        "",
        f"**今日大盘：** {idx_lines}",
        "",
    ]

    for item in items:
        h = item["history"]
        cur = item["current"]

        buy_price = h["price"]
        old_rate  = h["rate"]
        direction = h["direction"]

        if cur is not None and pd.notna(cur.get("净值")) and float(cur.get("净值", 0)) > 0:
            cur_nav = float(cur["净值"])
            if direction == "discount":
                actual_profit = (cur_nav - buy_price) / buy_price * 100 - _BUY_COMM - _REDEEM_FEE
            else:
                cur_price = float(cur["场内价"])
                actual_profit = (cur_price - buy_price) / buy_price * 100 - _SUB_FEE - _SELL_COMM
            nav_str = f"{cur_nav:.4f}"
            has_data = True
        else:
            actual_profit = None
            nav_str = "数据不可用"
            has_data = False

        if not has_data:
            advice = "**数据获取失败，请手动查看净值后决定是否赎回**"
            ai_sell_prompt = ""
        elif direction == "discount":
            if actual_profit is not None and actual_profit > 0:
                advice = f"**建议：今日赎回** ✓（预估净利润 {actual_profit:.2f}%）"
            elif actual_profit is not None and actual_profit > -0.5:
                advice = f"**建议：赎回（小幅亏损 {actual_profit:.2f}%，止损为主）**"
            else:
                advice = f"**建议：暂缓赎回**（净值跌幅 {actual_profit:.2f}%，可等待回升）"

            ai_sell_prompt = (
                f"我昨日以 {buy_price:.3f} 买入了 {h['name']}（{h['code']}）进行折价套利，"
                f"今日净值为 {nav_str}，大盘今日{idx_lines}。"
                f"预估赎回后净利润约 {actual_profit:.2f}%。"
                f"请明确告诉我：今日赎回还是继续持有？只回答【赎回】或【持有】，附一句理由。"
            )
        else:
            cur_price_str = f"{float(cur['场内价']):.3f}" if cur is not None else "未知"
            advice = f"**建议：查看场内价后决定是否卖出**（当前场内价 {cur_price_str}）"
            ai_sell_prompt = (
                f"我昨日申购了 {h['name']}（{h['code']}）进行溢价套利，"
                f"申购价（净值）约 {buy_price:.3f}，当前场内价 {cur_price_str}，"
                f"大盘今日{idx_lines}。"
                f"请明确告诉我：今日卖出还是继续持有？只回答【卖出】或【持有】，附一句理由。"
            )

        blocks += [
            "---",
            f"### {h['代码'] if '代码' in h else h['code']} {h['name']}",
            f"昨日买入：{buy_price:.3f}  |  当前净值：{nav_str}  |  原折溢价：{old_rate:+.2f}%",
            "",
            advice,
        ]
        if ai_sell_prompt:
            blocks += [
                "",
                "> **复制下方指令发给 AI：**",
                "",
                "```",
                ai_sell_prompt,
                "```",
            ]
        blocks.append("")

    return "\n".join(blocks)
