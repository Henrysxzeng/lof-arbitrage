# LOF Arbitrage Monitor · LOF基金套利监控系统

![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![GitHub Actions](https://img.shields.io/badge/CI-GitHub%20Actions-brightgreen)
![Data Sources](https://img.shields.io/badge/Data-EastMoney%20%7C%20Sina%20%7C%20fundgz-orange)
![License](https://img.shields.io/badge/License-MIT-yellow)

全自动 A 股 LOF 基金折价套利监控系统。交易日每 5 分钟扫描全市场约 350 只 LOF 基金，发现有效套利机会后即时推送微信通知，附带操作步骤与 AI 辅助分析指令。

*Automated A-share LOF fund discount arbitrage monitor. Scans ~350 LOF funds every 5 minutes during trading hours, delivers WeChat alerts with step-by-step instructions and AI analysis prompts.*

---

## 套利原理 / How It Works

LOF（上市开放式基金）同时在交易所（场内）和基金公司（场外）流通，两个渠道价格出现偏差时存在套利空间：

```
折价套利：场内价 < 净值
  → 场内低价买入 → 次日场外按净值赎回 → 赚取价差
```

*LOF (Listed Open-End Funds) trade both on-exchange (like stocks) and off-exchange (via fund companies). When prices diverge, arbitrage is possible: buy cheap on-exchange, redeem at NAV off-exchange.*

---

## 系统架构 / Architecture

```
┌─────────────────────────────────────────────────────────────┐
│               GitHub Actions Cron (Free Tier)                │
│           交易日 09:25–15:05，每 5 分钟自动触发               │
└──────────────────────────┬──────────────────────────────────┘
                           │
          ┌────────────────▼────────────────┐
          │         三重数据源（容错）         │
          ├─────────────────────────────────┤
          │  主：东方财富 push2 实时行情       │
          │  备：东方财富备用节点              │
          │  底：新浪行情 + fundgz 估算净值    │
          └────────────────┬────────────────┘
                           │
          ┌────────────────▼────────────────┐
          │           信号过滤层（5 道关卡）   │
          ├─────────────────────────────────┤
          │  1. 折价率 ≥ 2.5%               │
          │  2. 仅限指数型 LOF               │
          │  3. 信号持续 ≥ 5 分钟            │
          │  4. 大盘跌幅 ≤ 1%               │
          │  5. 30 分钟推送冷却              │
          └────────────────┬────────────────┘
                           │
          ┌────────────────▼────────────────┐
          │        成本精算（自动化）          │
          ├─────────────────────────────────┤
          │  · 自动爬取每只基金真实赎回费率     │
          │  · 30 天本地缓存，无需人工维护     │
          │  · 净利润 = 折价 − 买入佣金 − 赎回费│
          │  · 信号强度分级（弱/中/强/极强）   │
          └────────────────┬────────────────┘
                           │
          ┌────────────────▼────────────────┐
          │            推送通知              │
          ├─────────────────────────────────┤
          │  · 微信即时推送（Server酱）        │
          │  · 广发易淘金具体操作步骤          │
          │  · 可直接发给 AI 的分析指令        │
          │  · 次日自动推送赎回/持有建议       │
          └─────────────────────────────────┘
```

---

## 核心功能 / Features

**信号质量**
- 5 道过滤关卡消除假信号，仅推送高置信度机会
- 仅限指数型 LOF（持仓透明，估算净值可信）
- 持续性验证：同一信号连续出现 ≥ 2 次扫描（5 分钟）方触发
- 大盘跌幅 > 1% 时全部阻断，回避 T+1 净值风险

**成本精算**
- 自动爬取东方财富各基金真实赎回费率（非统一假设）
- 30 天本地缓存，首次查询后无需重复请求
- 净利润实时计算，按信号强度分级展示

**三重数据源**
- 东方财富实时行情（主）→ 备用节点 → 新浪财经 + fundgz（兜底）
- 任意单一数据源故障自动切换，全天候可用

**闭环追踪**
- 记录每条推送的买入价格
- 次日自动拉取最新净值，推送"今日赎回"或"暂缓赎回"建议

---

## 技术栈 / Tech Stack

| 类别 | 技术 |
|------|------|
| 语言 | Python 3.11 |
| 调度 | GitHub Actions Cron |
| 主数据源 | 东方财富 push2 实时 API |
| 备用数据源 | 新浪财经 hq API + fundgz.1234567.com.cn |
| 费率数据 | 东方财富基金详情页（自动解析）|
| 通知 | Server酱 WeChat Push |
| 依赖 | pandas · requests · pytz |
| 基础设施成本 | **¥0**（GitHub Actions 免费额度） |

---

## 快速开始 / Quick Start

### 1. Fork 本仓库

### 2. 获取 Server酱 SendKey

登录 [sct.ftqq.com](https://sct.ftqq.com)，微信扫码即可获取 SendKey，无需实名认证，免费。

### 3. 配置 GitHub Secret

```
仓库 → Settings → Secrets and variables → Actions → New repository secret
Name:  SENDKEY
Value: 你的 SendKey（格式：SCTxxxxxxx）
```

### 4. 启用 Actions

仓库 → Actions → 启用工作流，每个交易日自动运行。

### 本地运行 / Local Run

```bash
git clone https://github.com/Henrysxzeng/lof-arbitrage
cd lof-arbitrage
pip install -r requirements.txt

# Windows PowerShell
$env:SENDKEY = "你的SendKey"

# 强制运行（忽略交易时段限制）
python main.py --force

# 完整测试含推送
python test_run.py --notify
```

---

## 信号判断逻辑 / Signal Logic

### 触发条件（全部满足）

| # | 条件 | 说明 |
|---|------|------|
| 1 | 折价率 ≥ **2.5%** | 典型净利约 2%，安全边际充足 |
| 2 | 仅限**指数型** LOF | 主动管理基金估算净值误差大，排除 |
| 3 | 信号持续 **≥ 5 分钟** | 连续两次扫描确认，过滤瞬时假信号 |
| 4 | 大盘跌幅 **≤ 1%** | 跌幅过大时 T+1 净值风险超过套利收益 |
| 5 | 冷却期 **30 分钟** | 同一基金不重复轰炸 |

### 成本模型

```
净利润 = 折价率 − 场内买入佣金(0.025%) − 赎回费(自动查询，通常0.5%)

示例：折价 2.5%，赎回费 0.5%
  净利润 = 2.5% − 0.025% − 0.5% = 约 2%
```

---

## 推送示例 / Notification Preview

**买入提醒：**
```
【LOF套利】2 个机会 · 最优 2.87%

大盘：上证指数 3241 (+0.52%)  深证成指 10823 (+0.38%)
风险评估：低风险 — 大盘平稳，套利成功概率较高

─────────────────────────────────
[折价] 161725 招商中证白酒指数LOF

场内价   净值    折溢价率   扣费后净利
0.961   1.000   -3.9%    约 3.37% [极强]

操作（广发易淘金）：
1. 交易 → 买入 → 搜索 161725 → 限价委托
2. 次日：理财 → 场内基金 → 赎回

[AI 分析指令附于通知末尾，可直接发给 Claude/GPT]
```

**次日追踪：**
```
【LOF套利·昨日持仓】今日操作建议

161725 招商中证白酒LOF
昨日买入 0.961 · 今日净值 1.002
建议：今日赎回 ✓（净利 2.87%）
```

---

## 已知局限 / Known Limitations

- **冲击成本**：流动性较低的 LOF 大额买入会推高价格，系统过滤了日成交量 < 100 手的品种，但未精确估算冲击成本
- **T+1 净值风险**：买入次日净值可能因市场波动下跌，大盘跌幅 >1% 阻断机制提供部分保护，但无法完全消除
- **机构竞争**：专业套利机构反应更快，极高折价往往在数分钟内被消化，5 分钟持续性过滤一定程度上确保机会的真实性

---

## 风险提示 / Disclaimer

本项目仅供学习研究使用，不构成投资建议。LOF 套利存在市场风险，请在充分了解风险后自行决策。

*This project is for educational purposes only and does not constitute investment advice.*

---

## License

MIT
