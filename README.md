# LOF Arbitrage Monitor · LOF基金套利监控系统

![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![GitHub Actions](https://img.shields.io/badge/CI-GitHub%20Actions-brightgreen)
![License](https://img.shields.io/badge/License-MIT-yellow)

> 全自动检测 A 股 LOF 基金折溢价套利机会，交易时段每 5 分钟扫描全市场，发现机会即时推送微信通知并附带 AI 分析指令。

> An automated system that scans the entire A-share LOF fund market every 5 minutes during trading hours, detects premium/discount arbitrage opportunities, and delivers instant WeChat alerts with AI analysis prompts.

---

## 目录 / Contents

- [套利原理 / How Arbitrage Works](#套利原理)
- [系统架构 / Architecture](#系统架构)
- [功能特性 / Features](#功能特性)
- [技术栈 / Tech Stack](#技术栈)
- [快速开始 / Quick Start](#快速开始)
- [推送示例 / Notification Preview](#推送示例)

---

## 套利原理

LOF（上市开放式基金）同时在交易所（场内）和基金公司（场外）流通，两个渠道价格偶尔出现偏差：

```
折价套利：场内价 < 净值  →  场内低价买入，场外按净值赎回，赚取价差
溢价套利：场内价 > 净值  →  场外按净值申购，场内高价卖出，赚取价差
```

本系统实时监控全市场约 **350 只 LOF 基金**，在折溢价幅度覆盖全部手续费后仍有利润时发出提醒。

**How LOF Arbitrage Works**

LOF (Listed Open-End Funds) trade both on-exchange (like stocks) and off-exchange (via fund companies). When the two prices diverge:

```
Discount arb: exchange price < NAV  →  buy on-exchange, redeem off-exchange at NAV
Premium arb:  exchange price > NAV  →  subscribe off-exchange at NAV, sell on-exchange
```

---

## 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                  GitHub Actions (Cron)                   │
│              每5分钟 · 交易日 09:25–15:05                 │
└───────────────────────┬─────────────────────────────────┘
                        │
            ┌───────────▼───────────┐
            │     数据获取层         │
            │  (三重容错数据源)       │
            ├───────────────────────┤
            │ 1. 东方财富 push2 API  │  主数据源，全量 1500+ 只
            │ 2. 东方财富备用节点     │  push2 故障时切换
            │ 3. 新浪行情+fundgz     │  兜底，任何网络环境可用
            └───────────┬───────────┘
                        │
            ┌───────────▼───────────┐
            │     分析计算层         │
            ├───────────────────────┤
            │ · 折溢价率实时计算      │
            │ · 手续费成本扣除        │
            │ · 大盘风险评估          │
            │ · 流动性过滤            │
            └───────────┬───────────┘
                        │
            ┌───────────▼───────────┐
            │     推送通知层         │
            ├───────────────────────┤
            │ · Server酱 微信推送    │
            │ · 操作步骤（广发易淘金）│
            │ · AI 分析指令模板       │
            │ · 30分钟推送冷却        │
            └───────────┬───────────┘
                        │
            ┌───────────▼───────────┐
            │     次日跟踪层         │
            ├───────────────────────┤
            │ · 自动记录每次提醒      │
            │ · 次日对比当前净值      │
            │ · 推送赎回/持有建议     │
            └───────────────────────┘
```

---

## 功能特性

- **全市场覆盖**：扫描全部约 350 只 A 股 LOF 基金
- **三重数据源**：东方财富主/备 + 新浪财经兜底，确保高可用
- **成本感知**：自动扣除申购费、赎回费、交易佣金后计算净利润
- **大盘联动**：实时获取三大指数，评估市场风险等级
- **AI 辅助决策**：每条推送附带可直接发给 AI 的分析指令
- **次日自动跟踪**：记录历史提醒，次日推送是否执行赎回的建议
- **免费部署**：基于 GitHub Actions，零服务器成本

**Features**

- Full market scan of ~350 LOF funds every 5 minutes
- Triple data source failover for high availability
- Net profit calculation after all transaction fees
- Real-time market sentiment (CSI indices)
- Ready-to-use AI analysis prompt in every alert
- Next-day follow-up: automatic sell/hold recommendation
- Zero infrastructure cost via GitHub Actions

---

## 技术栈 / Tech Stack

| 类别 | 技术 |
|------|------|
| 语言 | Python 3.11 |
| 数据源 | 东方财富 push2 API · 新浪财经 hq API · fundgz.1234567.com.cn |
| 调度 | GitHub Actions Cron |
| 通知 | Server酱 (WeChat push) |
| 依赖 | pandas · requests · pytz |

---

## 快速开始 / Quick Start

### 1. Fork 本仓库

### 2. 获取 Server酱 SendKey

登录 [sct.ftqq.com](https://sct.ftqq.com)，微信扫码后复制 SendKey。

### 3. 配置 GitHub Secret

仓库 → Settings → Secrets and variables → Actions → New repository secret

```
Name:  SENDKEY
Value: 你的SendKey
```

### 4. 启用 Actions

仓库 → Actions → 启用工作流，每个交易日自动运行。

### 本地运行 / Local Run

```bash
git clone https://github.com/your-username/lof-arbitrage
cd lof-arbitrage
pip install -r requirements.txt

# 填入 SendKey
export SENDKEY=your_sendkey   # Linux/Mac
$env:SENDKEY="your_sendkey"   # Windows PowerShell

# 强制运行（忽略交易时段限制）
python main.py --force

# 完整测试（含通知发送）
python test_run.py --notify
```

---

## 推送示例 / Notification Preview

```
【LOF套利】3 个机会 · 最优 2.14%
LOF/ETF 套利提醒 10:32

大盘：上证指数 3241 (+0.52%)  深证成指 10823 (+0.38%)
风险评估：低风险 — 大盘平稳，套利成功概率较高

──────────────────────────────
[折价] 161725 招商中证白酒LOF

场内价    净值      折溢价率    扣费后净利
0.983    1.000     -1.70%    约 0.17%

操作步骤（广发易淘金）：
1. 交易 → 买入 → 搜索 161725 → 限价委托
2. 次日：理财 → 场内基金 → 赎回

[AI 分析指令已附带，复制发给 Claude/GPT 获取建议]
```

次日自动推送：
```
【LOF套利·昨日持仓】今日操作建议

161725 招商中证白酒LOF
昨日买入 0.983 · 今日净值 1.001
建议：今日赎回 ✓（预估净利润 0.18%）
```

---

## 风险提示 / Disclaimer

本项目仅供学习研究使用，不构成投资建议。LOF 套利存在 T+1 结算风险，市场大幅波动时净值可能在持仓期间发生不利变动。请在充分了解风险后自行决策。

*This project is for educational purposes only and does not constitute investment advice.*

---

## License

MIT
