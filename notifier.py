import requests
import pandas as pd
import logging
from datetime import datetime
import config

logger = logging.getLogger(__name__)

_URL = "https://sctapi.ftqq.com/{sendkey}.send"


def send(opportunities: pd.DataFrame) -> bool:
    if not config.SENDKEY:
        logger.error("config.py 中 SENDKEY 未填写")
        return False

    max_rate = opportunities['折溢价率'].abs().max()
    title = f"【LOF套利】{len(opportunities)} 个机会 · 最高 {max_rate:.2f}%"
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


def _build_markdown(df: pd.DataFrame) -> str:
    now = datetime.now().strftime('%H:%M:%S')
    has_nav = '净值' in df.columns

    header = "| 代码 | 名称 | 场内价 | 净值 | 折溢价率 | 建议操作 |"
    sep    = "|:---:|:---:|:---:|:---:|:---:|:---:|"

    rows = []
    for _, r in df.iterrows():
        rate = r['折溢价率']
        tag = "[溢]" if rate > 0 else "[折]"
        nav_str = f"{r['净值']:.4f}" if has_nav and pd.notna(r.get('净值')) else "—"
        rows.append(
            f"| {r['代码']} | {str(r['名称'])[:10]} "
            f"| {r['场内价']:.3f} | {nav_str} "
            f"| {tag} **{rate:+.2f}%** | {r['操作']} |"
        )

    return "\n".join([
        f"## LOF/ETF 套利机会  ({now})",
        "",
        header, sep,
        *rows,
        "",
        "---",
        "> **风险提示**：套利前请计算申购费(0.1~1%)+赎回费(0.5%)+冲击成本",
        "> 建议净折溢价超过 **1%** 再操作；T+1 到账期间价格仍可能变动",
    ])
