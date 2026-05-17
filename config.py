# ==================================================
# LOF/ETF 套利检测配置
# ==================================================

import os
# 优先读环境变量（GitHub Actions 用），本地测试用下面的硬编码值
SENDKEY = os.environ.get("SENDKEY", "")  # 本地填入，部署时通过 GitHub Secrets 注入

# 套利触发阈值（%）
# 默认 0.8%，扣除申购费+赎回费后仍有利润空间
PREMIUM_THRESHOLD = 99.0   # 溢价套利对散户不可行（T+2时差），实际关闭
DISCOUNT_THRESHOLD = -2.5  # 折价套利阈值：2.5%折价扣除成本后净利约1%，安全边际足够

# 流动性过滤：成交量太小的基金套利风险高，直接过滤
MIN_VOLUME = 100  # 单位：手

# 推送控制：同一只基金 N 分钟内不重复推送
COOLDOWN_MINUTES = 30

# 日志文件路径
LOG_FILE = "arbitrage.log"
