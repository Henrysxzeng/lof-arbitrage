# ==================================================
# LOF/ETF 套利检测配置
# ==================================================

import os
# 优先读环境变量（GitHub Actions 用），本地测试用下面的硬编码值
SENDKEY = os.environ.get("SENDKEY", "SCT350719T56ZEr49emeToUEl6kZr7BlhR")

# 套利触发阈值（%）
# 默认 0.8%，扣除申购费+赎回费后仍有利润空间
PREMIUM_THRESHOLD = 0.8    # 溢价超过此值触发提醒（正值）
DISCOUNT_THRESHOLD = -0.8  # 折价超过此值触发提醒（负值）

# 流动性过滤：成交量太小的基金套利风险高，直接过滤
MIN_VOLUME = 100  # 单位：手

# 推送控制：同一只基金 N 分钟内不重复推送
COOLDOWN_MINUTES = 30

# 日志文件路径
LOG_FILE = "arbitrage.log"
