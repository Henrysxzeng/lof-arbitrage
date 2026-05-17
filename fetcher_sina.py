"""
备用数据源：新浪行情（场内价）+ fundgz（估算净值）
当东方财富 push2 不可用时自动启用。
"""
from __future__ import annotations
import re
import json
import requests
import pandas as pd
import logging
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://finance.sina.com.cn/",
}

# 东方财富 fundRankHandler（比 push2 更稳定的 REST 接口）
_EM_RANK_URL = (
    "https://fund.eastmoney.com/data/rankhandler.aspx"
    "?op=ph&dt=kf&ft=lof&rs=&gs=0&sc=rzdf&st=desc&pi=1&pn=2000&dx=1&v=0.1"
)
_SINA_PRICE_URL = "https://hq.sinajs.cn/list={symbols}"
_FUNDGZ_URL = "http://fundgz.1234567.com.cn/js/{code}.js"


# ── Step 1: 获取 LOF 基金代码列表 ─────────────────────────

_FUNDCODE_JS = "https://fund.eastmoney.com/js/fundcode_search.js"

def _get_lof_codes_em() -> list[tuple[str, str]]:
    """
    从东方财富 fundcode_search.js 提取所有场内 LOF 代码（以1或5开头）。
    返回 [(exchange, code), ...] 如 [('sz','161725'), ...]
    """
    try:
        resp = requests.get(_FUNDCODE_JS, headers=_HEADERS, timeout=15)
        resp.encoding = "utf-8"
        # 匹配 "(LOF)" 且代码以 1 或 5 开头（场内交易代码）
        raw_codes = re.findall(r'"([15]\d{5})",[^,]*,[^,]*\(LOF\)', resp.text)
        codes = [("sh" if c.startswith("5") else "sz", c) for c in set(raw_codes)]
        logger.info(f"从 fundcode_search.js 获取 {len(codes)} 只 LOF 代码")
        return codes
    except Exception as e:
        logger.warning(f"获取 LOF 代码列表失败: {e}")
        return []


# ── Step 2: 新浪批量获取场内价 ───────────────────────────

def _get_prices_sina(codes: list[tuple[str, str]]) -> dict[str, float]:
    """
    批量查询新浪行情，返回 {code: price}。
    每批最多 100 只。
    """
    prices: dict[str, float] = {}
    batch_size = 100
    for i in range(0, len(codes), batch_size):
        batch = codes[i:i + batch_size]
        symbols = ",".join(f"{ex}{code}" for ex, code in batch)
        try:
            resp = requests.get(
                _SINA_PRICE_URL.format(symbols=symbols),
                headers=_HEADERS, timeout=10
            )
            resp.encoding = "gbk"
            for line in resp.text.strip().split("\n"):
                line = line.strip()
                if not line or '"' not in line:
                    continue
                # var hq_str_sz161725="白酒基金,0.597,0.601,0.588,..."
                key_match = re.search(r'hq_str_[a-z]{2}(\d{6})', line)
                val_match = re.search(r'"([^"]+)"', line)
                if not key_match or not val_match:
                    continue
                code = key_match.group(1)
                fields = val_match.group(1).split(",")
                if len(fields) > 3:
                    try:
                        price = float(fields[3])  # 当前价
                        if price > 0:
                            prices[code] = price
                    except ValueError:
                        pass
        except Exception as e:
            logger.warning(f"Sina price batch failed: {e}")
    logger.info(f"新浪获取到 {len(prices)} 只价格")
    return prices


# ── Step 3: fundgz 并发获取估算净值 ──────────────────────

def _fetch_one_nav(code: str) -> tuple[str, Optional[dict]]:
    try:
        resp = requests.get(
            _FUNDGZ_URL.format(code=code),
            headers=_HEADERS, timeout=5
        )
        match = re.search(r'jsonpgz\((\{.*?\})\)', resp.text)
        if match:
            data = json.loads(match.group(1))
            return code, data
    except Exception:
        pass
    return code, None


def _get_navs_fundgz(codes: list[str], max_workers: int = 20) -> dict[str, dict]:
    """并发获取估算净值，返回 {code: {dwjz, gsz, name, ...}}"""
    results: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_fetch_one_nav, code): code for code in codes}
        for fut in as_completed(futures):
            code, data = fut.result()
            if data:
                results[code] = data
    logger.info(f"fundgz 获取到 {len(results)} 只净值")
    return results


# ── 组合: 计算折溢价率 ────────────────────────────────────

def get_raw_data_sina() -> Optional[pd.DataFrame]:
    """
    完整备用流程：
    1. 从 EM rankhandler 获取 LOF 代码列表
    2. 新浪获取场内价
    3. fundgz 获取估算净值
    4. 计算折溢价率，返回标准 DataFrame
    """
    codes = _get_lof_codes_em()
    if not codes:
        logger.error("无法获取 LOF 代码列表")
        return None

    prices   = _get_prices_sina(codes)
    nav_data = _get_navs_fundgz([c for _, c in codes])

    rows = []
    for exchange, code in codes:
        price = prices.get(code)
        nav   = nav_data.get(code)
        if price is None or nav is None:
            continue
        try:
            # 优先用交易时段估算净值 gsz，收盘后用 dwjz
            nav_val = float(nav.get("gsz") or nav.get("dwjz", 0))
            if nav_val <= 0:
                continue
            premium = (price - nav_val) / nav_val * 100
            rows.append({
                "代码":    code,
                "名称":    nav.get("name", ""),
                "场内价":  price,
                "净值":    nav_val,
                "折溢价率": round(premium, 4),
                # 不含成交量列，detector 会跳过成交量过滤
                "市场":    1 if exchange == "sh" else 0,
            })
        except (ValueError, TypeError):
            pass

    if not rows:
        return None
    df = pd.DataFrame(rows)
    logger.info(f"备用数据源合并完成，共 {len(df)} 条有效数据")
    return df
