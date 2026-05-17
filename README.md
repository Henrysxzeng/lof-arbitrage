# LOF Arbitrage Monitor · LOF基金套利监控系统

![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![GitHub Actions](https://img.shields.io/badge/Scheduler-GitHub%20Actions-brightgreen)
![Data](https://img.shields.io/badge/Data-EastMoney%20%7C%20Sina%20%7C%20Tencent-orange)
![License](https://img.shields.io/badge/License-MIT-yellow)

全自动 A 股 LOF 基金折价套利监控系统。交易日每 5 分钟扫描全市场约 350 只 LOF 基金（含黄金、白银等商品 LOF），发现有效套利机会即时推送微信通知，附带逐基金真实费率计算、操作步骤及 AI 分析指令。

*Automated A-share LOF fund discount arbitrage monitor. Scans ~350 LOF funds (including commodity LOFs) every 5 minutes during trading hours, with real per-fund fee calculation, operation guidance, and AI analysis prompts.*

---

## 项目亮点 / Highlights

- **三重数据源容错**：东方财富主/备节点 → 新浪行情 + fundgz，任意单点故障自动切换
- **逐基金费率自动爬取**：从东方财富基金详情页解析真实赎回费率，30 天缓存，无需手动维护
- **5 道信号过滤关卡**：折价阈值 + 指数型白名单 + 5 分钟持续性验证 + 大盘趋势过滤 + 冷却控制
- **执行延迟敏感性分析**：量化"扫描延迟 + 人工反应"对套利收益的影响，验证安全边际
- **5 年历史回测**：腾讯财经 K 线 + 东方财富净值，实证验证信号频率与收益分布
- **零基础设施成本**：基于 GitHub Actions 免费额度，月均用量约 80 分钟（额度 2000 分钟）

---

## 套利原理 / How It Works

```
折价套利：场内价 < 净值
  → 场内低价买入 → 次日场外按净值赎回 → 赚取价差
```

LOF 同时在交易所（场内）和基金公司（场外）流通，两个渠道价格偶尔出现偏差，尤其在：
- 市场恐慌性踩踏（场内价超跌）
- 商品价格剧烈波动（黄金、白银 LOF 的场内外价差）

*LOF (Listed Open-End Funds) trade both on-exchange and off-exchange. When prices diverge — especially during market panic or commodity price spikes — discount arbitrage is possible.*

---

## 系统架构 / Architecture

```
┌──────────────────────────────────────────────────────┐
│          GitHub Actions Cron（交易日 09:25–15:05）     │
│                    每 5 分钟触发                        │
└──────────────────────┬───────────────────────────────┘
                       │
        ┌──────────────▼──────────────┐
        │       三重数据源（容错）      │
        │  东方财富 push2              │ ← 主（全量 ETF/LOF）
        │  东方财富备用节点             │ ← 自动切换
        │  新浪行情 + fundgz.1234567   │ ← 兜底（任何网络可用）
        └──────────────┬──────────────┘
                       │
        ┌──────────────▼──────────────┐
        │       5 道信号过滤           │
        │  ① 折价率 ≥ 2.5%            │
        │  ② 仅 A 股指数型 + 商品 LOF  │
        │  ③ 信号持续 ≥ 5 分钟         │
        │  ④ 大盘跌幅 ≤ 1%             │
        │  ⑤ 30 分钟推送冷却           │
        └──────────────┬──────────────┘
                       │
        ┌──────────────▼──────────────┐
        │       成本精算               │
        │  自动爬取每只基金真实赎回费率  │
        │  净利润 = 折价 − 1.525%      │
        │  信号强度分级（弱/中/强/极强） │
        └──────────────┬──────────────┘
                       │
        ┌──────────────▼──────────────┐
        │       微信推送               │
        │  操作步骤（广发易淘金）        │
        │  冲击成本估算                 │
        │  可直接发给 AI 的分析指令      │
        │  次日自动推送赎回/持有建议     │
        └──────────────────────────────┘
```

---

## 回测结果 / Backtest Results（2020–2025，5 年）

| 基金类型 | 代表品种 | 最大折价 | >2.5%天数/5年 | 年均约 |
|---------|---------|--------|------------|------|
| A 股宽基指数 LOF | 嘉实沪深300 | 1.88% | 0 天 | 0 次 |
| A 股主题 LOF | 兴全趋势 | 3.56% | 1 天 | 0.2 次 |
| **商品 LOF（白银）** | **白银LOF** | **4.49%** | **3 天** | **~0.6 次** |

**执行延迟敏感性**（以真实 3.56% 折价案例验证）：

| 延迟导致折价收敛 | 有效折价 | 净利润 | 结论 |
|--------------|--------|-------|------|
| 0%（无延迟） | 3.56% | +1.53% | ✅ |
| 0.5%（约 2 分钟） | 3.06% | +1.05% | ✅ |
| 1.0%（约 5 分钟） | 2.56% | +0.56% | ✅ |
| 1.5%（约 8-10 分钟） | 2.06% | +0.08% | ⚠️ 勉强 |

安全边际：初始折价 3.5%+ 时，即使人工执行延迟 10 分钟仍可盈利。

---

## 技术栈 / Tech Stack

| 类别 | 技术 |
|------|------|
| 语言 | Python 3.11 |
| 调度 | GitHub Actions Cron |
| 实时数据 | 东方财富 push2 API |
| 备用数据 | 新浪财经 hq API + fundgz.1234567.com.cn |
| 历史数据 | 腾讯财经 K 线 API + 东方财富历史净值 |
| 费率数据 | 东方财富基金详情页（自动解析 HTML） |
| 通知 | Server酱（WeChat Push） |
| 依赖 | pandas · requests · pytz |
| 基础设施成本 | **¥0** |

---

## 快速开始 / Quick Start

### 1. Fork 本仓库

### 2. 获取 Server酱 SendKey

登录 [sct.ftqq.com](https://sct.ftqq.com)，微信扫码，免费获取 SendKey。

### 3. 配置 GitHub Secret

```
Settings → Secrets and variables → Actions → New repository secret
Name:   SENDKEY
Value:  你的 SendKey
```

### 4. 启用 Actions，每个交易日自动运行

### 本地运行

```bash
pip install -r requirements.txt
export SENDKEY=your_sendkey       # Linux/Mac
$env:SENDKEY="your_sendkey"       # Windows PowerShell

python main.py --force            # 强制运行（忽略交易时段）
python test_run.py --notify       # 完整测试含推送
python backtest.py 161726 2020-01-01 2025-12-31 2.5   # 回测指定基金
python calc.py 161725 2.8 50000   # 计算指定折价下的实际利润
```

---

## 文件说明 / File Structure

```
├── main.py           主程序（扫描 + 过滤 + 推送 + 次日跟踪）
├── fetcher.py        东方财富实时数据（三重容错）
├── fetcher_sina.py   新浪 + fundgz 备用数据源
├── detector.py       信号过滤（5道关卡）
├── notifier.py       微信推送（费率精算 + 操作步骤 + AI指令）
├── fee_fetcher.py    自动爬取逐基金赎回费率
├── market.py         大盘指数（风险评估）
├── config.py         配置（阈值、冷却时间等）
├── backtest.py       历史回测（含执行延迟敏感性分析）
├── calc.py           利润计算器 CLI
├── STRATEGY.md       完整策略逻辑说明（含回测结论）
└── .github/workflows/lof_arbitrage.yml   GitHub Actions 配置
```

---

## 策略局限性 / Known Limitations

- 日K回测无法验证盘中信号的实际可执行性，分钟级历史 gsz 数据无免费来源
- 极端行情时冲击成本高于正常市场，实际收益低于回测值
- 策略为低频捕捉型（年均 0-2 次），不适合作为稳定收入来源

---

## 风险提示 / Disclaimer

本项目仅供学习研究，不构成投资建议。

---

## License

MIT
