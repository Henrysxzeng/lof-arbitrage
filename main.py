from __future__ import annotations
import logging
import json
import os
import sys
import tempfile
from datetime import datetime, time

import pandas as pd
import pytz

import config
from fetcher import get_raw_data, normalize
from detector import detect
from market import get_indices, risk_level
from notifier import send, send_followup

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(config.LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

_TZ            = pytz.timezone("Asia/Shanghai")
_COOLDOWN_FILE = os.path.join(tempfile.gettempdir(), "lof_cooldown.json")
_HISTORY_FILE  = os.path.join(tempfile.gettempdir(), "lof_history.json")


# ── 交易时段判断 ──────────────────────────────────────────

def _is_trading() -> bool:
    now = datetime.now(_TZ)
    if now.weekday() >= 5:
        return False
    t = now.time()
    return (time(9, 25) <= t <= time(11, 35)) or (time(12, 55) <= t <= time(15, 5))


# ── 冷却控制 ──────────────────────────────────────────────

def _load_json(path: str) -> list | dict:
    try:
        if os.path.exists(path):
            with open(path) as f:
                return json.load(f)
    except Exception:
        pass
    return {} if "cooldown" in path else []


def _save_json(path: str, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


def _filter_cooldown(opps: pd.DataFrame, cooldown: dict) -> list:
    now_ts = datetime.now().timestamp()
    return [
        row for _, row in opps.iterrows()
        if now_ts - cooldown.get(str(row["代码"]), 0) > config.COOLDOWN_MINUTES * 60
    ]


# ── 历史记录（次日跟踪） ───────────────────────────────────

def _record_alerts(opps: pd.DataFrame):
    history = _load_json(_HISTORY_FILE)
    today = datetime.now(_TZ).strftime("%Y-%m-%d")
    for _, row in opps.iterrows():
        history.append({
            "date":          today,
            "code":          str(row["代码"]),
            "name":          str(row["名称"]),
            "price":         float(row["场内价"]),
            "nav":           float(row["净值"]) if "净值" in opps.columns and pd.notna(row.get("净值")) else None,
            "rate":          float(row["折溢价率"]),
            "direction":     "discount" if row["折溢价率"] < 0 else "premium",
            "followup_sent": False,
        })
    _save_json(_HISTORY_FILE, history)


def _check_followup(df_current: pd.DataFrame | None, indices: dict):
    history = _load_json(_HISTORY_FILE)
    today = datetime.now(_TZ).strftime("%Y-%m-%d")
    pending = [h for h in history if not h["followup_sent"] and h["date"] < today]
    if not pending:
        return

    items = []
    for h in pending:
        cur = None
        if df_current is not None and not df_current.empty:
            matches = df_current[df_current["代码"] == h["code"]]
            if not matches.empty:
                cur = matches.iloc[0]
        items.append({"history": h, "current": cur})
        h["followup_sent"] = True

    send_followup(items, indices)
    _save_json(_HISTORY_FILE, history)
    logger.info(f"次日跟踪推送：{len(items)} 只")


# ── 主逻辑 ────────────────────────────────────────────────

def main(force: bool = False):
    if not force and not _is_trading():
        logger.info("非交易时段，跳过")
        return

    logger.info("===== 套利扫描开始 =====")

    # 并行获取数据
    raw     = get_raw_data()
    indices = get_indices()
    risk    = risk_level(indices)

    df = normalize(raw) if raw is not None else None

    # 先检查昨天的持仓跟踪
    _check_followup(df, indices)

    if df is None or df.empty:
        logger.info("无有效数据，结束")
        return

    opps = detect(df)
    if opps.empty:
        logger.info("无套利机会")
        return

    cooldown = _load_json(_COOLDOWN_FILE)
    new_opps = _filter_cooldown(opps, cooldown)
    if not new_opps:
        logger.info(f"{len(opps)} 个机会均在冷却期")
        return

    opp_df = pd.DataFrame(new_opps)
    logger.info(f"推送 {len(opp_df)} 个新机会")

    if send(opp_df, indices, risk):
        now_ts = datetime.now().timestamp()
        for row in new_opps:
            cooldown[str(row["代码"])] = now_ts
        _save_json(_COOLDOWN_FILE, cooldown)
        _record_alerts(opp_df)


if __name__ == "__main__":
    force_flag = "--force" in sys.argv or "-f" in sys.argv
    main(force=force_flag)
