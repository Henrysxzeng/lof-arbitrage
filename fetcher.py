"""
直接调用东方财富 API 获取 ETF/LOF 实时行情，无需 akshare。
数据源：东方财富 push2 接口（同 fund.eastmoney.com 网页所用接口）
"""
import time
import requests
import pandas as pd
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_URL = "https://push2.eastmoney.com/api/qt/clist/get"
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0",
    "Referer": "https://fund.eastmoney.com/",
}
# 东方财富网页标准 token，无需登录
_UT = "bd1d9ddb04089700cf9c27f6f7426281"

# fs 参数：MK0021/22 = ETF(沪/深), MK0023/24 = LOF(沪/深)
_FS_ALL  = "b:MK0021,b:MK0022,b:MK0023,b:MK0024"
_FS_LOF  = "b:MK0023,b:MK0024"

# 东方财富字段 → 我们的列名
_FIELD_MAP = {
    "f12":  "代码",
    "f14":  "名称",
    "f2":   "场内价",
    "f115": "净值",
    "f9":   "折溢价率",   # premium/discount %
    "f5":   "成交量",     # 单位：手
    "f3":   "涨跌幅",
    "f13":  "市场",       # 1=SH  0=SZ
}


def get_raw_data(lof_only: bool = False) -> Optional[pd.DataFrame]:
    """
    从东方财富拉取实时行情。
    lof_only=True 时只取 LOF 基金；默认 ETF+LOF 全取。
    """
    params = {
        "pn": 1, "pz": 10000, "po": 1, "np": 1,
        "fltt": 2, "invt": 2,
        "ut": _UT,
        "fid": "f3",
        "fs": _FS_LOF if lof_only else _FS_ALL,
        "fields": ",".join(_FIELD_MAP.keys()),
        "_": int(time.time() * 1000),
    }
    for attempt in range(3):
        try:
            resp = requests.get(_URL, params=params, headers=_HEADERS, timeout=15)
            resp.raise_for_status()
            items = resp.json().get("data", {}).get("diff", [])
            if not items:
                logger.warning("API 返回空列表")
                return None
            df = pd.DataFrame(items).rename(columns=_FIELD_MAP)
            logger.info(f"获取到 {len(df)} 条记录")
            return df
        except Exception as e:
            logger.warning(f"第 {attempt+1} 次请求失败: {e}")
            if attempt < 2:
                time.sleep(5)
    logger.error("数据获取失败，已重试 3 次")
    return None


def normalize(df: pd.DataFrame) -> Optional[pd.DataFrame]:
    """清洗数值类型，过滤停牌及无折溢价率数据"""
    if df is None or df.empty:
        return None

    for col in ["场内价", "折溢价率", "成交量", "净值", "涨跌幅"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["场内价", "折溢价率"])
    df = df[df["场内价"] > 0]
    return df.reset_index(drop=True)
