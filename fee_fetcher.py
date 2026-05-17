"""
自动从东方财富查询 LOF 基金短期赎回费率（持有 <7 天）。
结果缓存 30 天，避免重复请求。
"""
from __future__ import annotations
import re
import json
import os
import time
import tempfile
import requests
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_CACHE_FILE = os.path.join(tempfile.gettempdir(), "lof_fee_cache.json")
_CACHE_TTL  = 30 * 24 * 3600  # 30 天
_DEFAULT_FEE = 1.5             # 查不到时使用最保守值
_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://fundf10.eastmoney.com/",
}


def _load_cache() -> dict:
    try:
        if os.path.exists(_CACHE_FILE):
            with open(_CACHE_FILE, encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _save_cache(cache: dict):
    with open(_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False)


def _fetch_fee_from_web(code: str) -> Optional[float]:
    """从东方财富费率页面解析 <7 天赎回费率"""
    try:
        url = f"https://fundf10.eastmoney.com/jjfl_{code}.html"
        resp = requests.get(url, headers=_HEADERS, timeout=10)
        resp.encoding = "utf-8"
        html = resp.text

        # 找赎回费表格
        # 格式：<td>小于7日</td><td>1.50%</td>
        match = re.search(
            r'小于7[日天][^<]*</td>\s*<td[^>]*>([\d.]+)%</td>',
            html, re.IGNORECASE
        )
        if match:
            fee = float(match.group(1))
            logger.info(f"{code} 赎回费(<7天) = {fee}%")
            return fee

        # 有些基金写法是「7日以内」
        match2 = re.search(
            r'7[日天]以内[^<]*</td>\s*<td[^>]*>([\d.]+)%</td>',
            html
        )
        if match2:
            fee = float(match2.group(1))
            logger.info(f"{code} 赎回费(<7天) = {fee}%（7日以内）")
            return fee

        logger.debug(f"{code} 未找到 <7天 赎回费，使用默认 {_DEFAULT_FEE}%")
        return None
    except Exception as e:
        logger.debug(f"{code} 费率查询失败: {e}")
        return None


def get_redemption_fee(code: str) -> float:
    """
    获取基金短期赎回费率（持有 <7 天）。
    优先查缓存，缓存过期或不存在时从网络获取。
    """
    # 先查 config 手动覆盖表
    try:
        import config
        if str(code) in config.FUND_REDEMPTION_FEE:
            return config.FUND_REDEMPTION_FEE[str(code)]
    except (ImportError, AttributeError):
        pass

    cache = _load_cache()
    entry = cache.get(str(code))
    now = time.time()

    if entry and now - entry.get("ts", 0) < _CACHE_TTL:
        return entry["fee"]

    fee = _fetch_fee_from_web(code)
    if fee is None:
        fee = _DEFAULT_FEE

    cache[str(code)] = {"fee": fee, "ts": now}
    _save_cache(cache)
    return fee


def prefetch_fees(codes: list[str], max_workers: int = 10):
    """批量预取费率（并发），在检测到套利机会后调用"""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    cache = _load_cache()
    now = time.time()
    to_fetch = [c for c in codes
                if c not in cache or now - cache[c].get("ts", 0) > _CACHE_TTL]

    if not to_fetch:
        return

    logger.info(f"预取 {len(to_fetch)} 只基金费率...")
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_fetch_fee_from_web, c): c for c in to_fetch}
        for fut in as_completed(futures):
            code = futures[fut]
            fee = fut.result() or _DEFAULT_FEE
            cache[str(code)] = {"fee": fee, "ts": now}

    _save_cache(cache)
    logger.info("费率预取完成")
