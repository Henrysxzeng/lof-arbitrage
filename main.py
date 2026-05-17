import logging
import json
import os
import sys
import tempfile
from datetime import datetime, time

import pytz

import config
from fetcher import get_raw_data, normalize
from detector import detect
from notifier import send

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(config.LOG_FILE, encoding='utf-8'),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

_COOLDOWN_FILE = os.path.join(tempfile.gettempdir(), 'lof_arbitrage_cooldown.json')
_TZ = pytz.timezone('Asia/Shanghai')


def _is_trading_hours() -> bool:
    now = datetime.now(_TZ)
    if now.weekday() >= 5:
        return False
    t = now.time()
    morning   = time(9, 25) <= t <= time(11, 35)
    afternoon = time(12, 55) <= t <= time(15, 5)
    return morning or afternoon


def _load_cooldown() -> dict:
    try:
        if os.path.exists(_COOLDOWN_FILE):
            with open(_COOLDOWN_FILE) as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _save_cooldown(data: dict):
    with open(_COOLDOWN_FILE, 'w') as f:
        json.dump(data, f)


def _filter_cooldown(opportunities, cooldown: dict) -> list:
    now_ts = datetime.now().timestamp()
    return [
        row for _, row in opportunities.iterrows()
        if now_ts - cooldown.get(str(row['代码']), 0) > config.COOLDOWN_MINUTES * 60
    ]


def main(force: bool = False):
    if not force and not _is_trading_hours():
        logger.info("非交易时段，跳过")
        return

    logger.info("===== 开始套利扫描 =====")

    raw = get_raw_data()
    if raw is None:
        return

    df = normalize(raw)
    if df is None:
        return

    opportunities = detect(df)
    if opportunities.empty:
        logger.info("未发现套利机会")
        return

    cooldown = _load_cooldown()
    new_opps = _filter_cooldown(opportunities, cooldown)

    if not new_opps:
        logger.info(f"发现 {len(opportunities)} 个机会，但均在冷却期内")
        return

    import pandas as pd
    opp_df = pd.DataFrame(new_opps)
    logger.info(f"推送 {len(opp_df)} 个新机会")

    if send(opp_df):
        now_ts = datetime.now().timestamp()
        for row in new_opps:
            cooldown[str(row['代码'])] = now_ts
        _save_cooldown(cooldown)


if __name__ == '__main__':
    force_flag = '--force' in sys.argv or '-f' in sys.argv
    main(force=force_flag)
