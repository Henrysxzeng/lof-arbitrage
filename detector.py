import pandas as pd
import logging
import config

logger = logging.getLogger(__name__)


def detect(df: pd.DataFrame) -> pd.DataFrame:
    """筛选折溢价率超过阈值的套利机会"""
    if df is None or df.empty:
        return pd.DataFrame()

    # 过滤低流动性品种
    if '成交量' in df.columns:
        df = df[df['成交量'] >= config.MIN_VOLUME].copy()

    discount = df[df['折溢价率'] <= config.DISCOUNT_THRESHOLD].copy()
    discount['套利方向'] = '折价套利'
    discount['操作'] = '场内买入 → 场外赎回'

    premium = df[df['折溢价率'] >= config.PREMIUM_THRESHOLD].copy()
    premium['套利方向'] = '溢价套利'
    premium['操作'] = '场外申购 → 场内卖出'

    result = pd.concat([discount, premium], ignore_index=True)
    result = result.sort_values('折溢价率', key=abs, ascending=False)

    logger.info(
        f"扫描完成 | 折价: {len(discount)} 个 | 溢价: {len(premium)} 个"
    )
    return result
