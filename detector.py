import pandas as pd
import logging
import config

logger = logging.getLogger(__name__)

# 指数型基金名称关键词 —— 只有这些才允许套利（估算净值可信）
_INDEX_KEYWORDS = [
    "指数", "ETF联接",
    "沪深300", "中证500", "中证800", "中证1000", "中证100", "中证200",
    "上证50", "上证180", "创业板", "科创50", "北证50", "双创", "科创板",
    "红利", "价值",
]

# 排除关键词（即使含指数词也排除）
_EXCLUDE_KEYWORDS = [
    # 主动管理
    "主动", "精选灵活", "量化精选",
    # QDII（海外指数 LOF：汇率+隔夜行情导致估算净值误差可达2%+）
    "纳指", "纳斯达克", "标普", "MSCI", "恒生", "日经",
    "美国", "美股", "港股", "海外", "国际", "QDII",
    "德国", "法国", "英国", "亚太", "全球",
]


def _is_eligible(name: str) -> bool:
    """是否为可做套利的 A 股指数型 LOF（估算净值可信，非 QDII）"""
    name = str(name)
    if any(kw in name for kw in _EXCLUDE_KEYWORDS):
        return False
    return any(kw in name for kw in _INDEX_KEYWORDS)


def detect(df: pd.DataFrame) -> pd.DataFrame:
    """筛选折溢价率超过阈值的套利机会"""
    if df is None or df.empty:
        return pd.DataFrame()

    # 1. 只保留指数型 LOF（估算净值可信）
    if '名称' in df.columns:
        index_mask = df['名称'].apply(_is_eligible)
        filtered_out = (~index_mask).sum()
        df = df[index_mask].copy()
        logger.info(f"过滤主动管理型基金 {filtered_out} 只，剩余 {len(df)} 只指数型")

    # 2. 过滤低流动性品种
    if '成交量' in df.columns:
        df = df[df['成交量'] >= config.MIN_VOLUME].copy()

    # 3. 折价套利（溢价阈值设为99%实际关闭）
    discount = df[df['折溢价率'] <= config.DISCOUNT_THRESHOLD].copy()
    discount['套利方向'] = '折价套利'
    discount['操作'] = '场内买入 → 场外赎回'

    premium = df[df['折溢价率'] >= config.PREMIUM_THRESHOLD].copy()
    premium['套利方向'] = '溢价套利'
    premium['操作'] = '场外申购 → 场内卖出'

    result = pd.concat([discount, premium], ignore_index=True)
    result = result.sort_values('折溢价率', key=abs, ascending=False)

    logger.info(f"扫描完成 | 折价: {len(discount)} 个 | 溢价: {len(premium)} 个")
    return result
