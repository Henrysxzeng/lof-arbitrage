from __future__ import annotations
import requests
import logging

logger = logging.getLogger(__name__)

_URL = "https://hq.sinajs.cn/list=s_sh000001,s_sz399001,s_sz399006"
_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://finance.sina.com.cn/",
}
_KEY_MAP = {
    "sh000001": "sh",
    "sz399001": "sz",
    "sz399006": "cyb",
}
_NAME_MAP = {
    "sh": "上证指数",
    "sz": "深证成指",
    "cyb": "创业板指",
}


def get_indices() -> dict:
    """返回 {'sh': {'price': '3200', 'change_pct': -0.83}, ...}"""
    try:
        resp = requests.get(_URL, headers=_HEADERS, timeout=10)
        resp.encoding = "gbk"
        result = {}
        for line in resp.text.strip().split("\n"):
            line = line.strip()
            if '"' not in line:
                continue
            content = line.split('"')[1]
            parts = content.split(",")
            if len(parts) < 4:
                continue
            for key, short in _KEY_MAP.items():
                if key in line:
                    try:
                        result[short] = {
                            "name": _NAME_MAP[short],
                            "price": parts[1],
                            "change_pct": float(parts[3]),
                        }
                    except (ValueError, IndexError):
                        pass
        return result
    except Exception as e:
        logger.warning(f"获取指数失败: {e}")
        return {}


def risk_level(indices: dict) -> tuple[str, str]:
    """返回 (风险等级, 说明)"""
    if not indices:
        return "未知", "无法获取市场数据，请自行判断"

    worst = min((v["change_pct"] for v in indices.values()), default=0.0)

    if worst <= -2.0:
        return "高风险", f"大盘大跌 {worst:.1f}%，基金净值可能继续下滑，建议谨慎"
    elif worst <= -1.0:
        return "中等风险", f"大盘下跌 {worst:.1f}%，净值有一定下滑风险"
    elif worst >= 2.0:
        return "注意速度", f"大盘大涨 {worst:+.1f}%，折价可能快速收窄，需尽快下单"
    else:
        return "低风险", f"大盘平稳（{worst:+.1f}%），套利成功概率较高"
