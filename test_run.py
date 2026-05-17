# -*- coding: utf-8 -*-
"""
本地测试脚本：不受交易时段限制，逐步验证每个模块。
用法：python test_run.py [--notify]
  --notify  填好 config.py 的 token 后加此参数，实际发送微信通知
"""
import sys
import os
import io
import logging
import pandas as pd

# 强制 stdout 用 UTF-8，避免 Windows GBK 乱码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    stream=sys.stdout,
)

import config
from fetcher import get_raw_data, normalize
from detector import detect
from notifier import send, _build_buy_md as _build_markdown


def sep(title):
    print("\n" + "=" * 50)
    print(f"  {title}")
    print("=" * 50)


def step1_fetch():
    sep("STEP 1 · 数据获取")
    raw = get_raw_data()
    if raw is None:
        print("[WARN] 数据获取失败（可能是休市或海外IP限制），后续步骤用假数据继续")
        return None
    print(f"[OK] 获取 {len(raw)} 条数据")
    print(f"     列名: {list(raw.columns)}")
    print(f"\n     前 3 条样本:")
    print(raw.head(3).to_string(index=False))
    return raw


def step2_normalize(raw):
    sep("STEP 2 · 数据标准化")
    if raw is None:
        print("[SKIP] 无真实数据，跳过")
        return None
    df = normalize(raw)
    if df is None:
        print("[WARN] 标准化失败，列名适配有问题")
    print(f"[OK] 标准化后 {len(df)} 条")
    print(f"     折溢价率范围: {df['折溢价率'].min():.2f}% ~ {df['折溢价率'].max():.2f}%")
    print(f"     溢价 >0.5%: {(df['折溢价率'] > 0.5).sum()} 只")
    print(f"     折价 <-0.5%: {(df['折溢价率'] < -0.5).sum()} 只")
    print(f"\n     折溢价率绝对值最大的 5 只:")
    top5 = df.reindex(df['折溢价率'].abs().nlargest(5).index)
    cols = ['代码', '名称', '场内价', '净值', '折溢价率'] if '净值' in df.columns else ['代码', '名称', '场内价', '折溢价率']
    print(top5[cols].to_string(index=False))
    return df


def step3_detect(df):
    sep("STEP 3 · 套利机会检测")
    if df is None or df.empty:
        print("[SKIP] 无真实数据，跳过")
        return pd.DataFrame()

    orig_p, orig_d = config.PREMIUM_THRESHOLD, config.DISCOUNT_THRESHOLD
    config.PREMIUM_THRESHOLD = 0.1
    config.DISCOUNT_THRESHOLD = -0.1

    opps = detect(df)

    config.PREMIUM_THRESHOLD = orig_p
    config.DISCOUNT_THRESHOLD = orig_d

    if opps.empty:
        print("[INFO] 当前 0.1% 阈值下无机会（市场效率较高）")
        return opps

    print(f"[OK] 发现 {len(opps)} 个机会（阈值临时设为 +-0.1%）")
    show = ['代码', '名称', '场内价', '折溢价率', '套利方向']
    if '净值' in opps.columns:
        show.insert(3, '净值')
    print(opps[show].to_string(index=False))
    return opps


def step4_notify(opps, do_send):
    sep("STEP 4 · 推送通知")
    if opps.empty:
        opps = pd.DataFrame([{
            '代码': '161725', '名称': '招商白酒(测试)',
            '场内价': 0.985, '净值': 1.000, '折溢价率': -1.52,
            '套利方向': '折价套利', '操作': '场内买入 -> 场外赎回',
        }])
        print("[INFO] 无真实机会，使用假数据测试推送格式")

    print("--- 消息预览 ---")
    print(_build_markdown(opps, indices={}, risk=("低风险（测试）", "测试数据")))
    print("--- 预览结束 ---")

    if not do_send:
        print("\n[INFO] 未传入 --notify，跳过实际发送")
        print("       在 config.py 填好 PUSHPLUS_TOKEN 后加 --notify 参数即可发送")
        return

    if not config.SENDKEY:
        print("[FAIL] config.py 中 SENDKEY 为空")
        return

    ok = send(opps)
    print("[OK] 微信通知已发送！" if ok else "[FAIL] 发送失败，请检查 token")


if __name__ == '__main__':
    do_notify = '--notify' in sys.argv

    raw  = step1_fetch()
    df   = step2_normalize(raw)
    opps = step3_detect(df)
    step4_notify(opps, do_notify)

    sep("全部测试完成")
