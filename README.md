# 财经汇报搭建

每日美股盘前简报 + 盘中异动提醒，自动发送到 cheonghanghou@gmail.com。

完全跑在 GitHub Actions 云端，与本机电脑是否开机无关。

## 数据来源

- 行情（标普500/纳指/道指/VIX/中概股代理ETF KWEB/黄金/原油/美元指数/美元兑人民币）：Yahoo Finance 公开行情接口，免费、无需 Key。
- 新闻 + 财报日历：[Finnhub](https://finnhub.io/) 免费版 API（需要 Key）。
- 经济数据日历：Finnhub 免费版不提供，报告中会附上 investing.com 的链接供自行查看。

## 目录结构

- `lib/`：共用模块（Yahoo行情、Finnhub、发邮件、关键词匹配）
- `scripts/daily_briefing.py`：每日盘前简报主脚本
- `scripts/volatility_alert.py`：盘中异动监控主脚本
- `.github/workflows/`：两个 GitHub Actions 定时任务配置
- `reports/daily/`：每日简报归档
- `reports/alerts/`：盘中异动提醒归档
- `state/`：盘中异动监控的每日触发状态（用于去重）
- `send_email.py` / `.env`：本地手动测试发信用，不参与云端运行

## 触发时间

- **每日简报**：GitHub Actions 在 UTC 12:00-14:45 每15分钟运行一次，脚本内部判断纽约时间是否为9点整（自动处理夏令时/冬令时），命中且当天报告未生成才会执行抓取+发送。
- **盘中异动**：GitHub Actions 在 UTC 13:00-21:45 每30分钟运行一次，脚本内部判断是否处于纽约时间9:00-16:30交易时段。

触发条件满足任一即发送提醒（同一天同档位/同一新闻不重复提醒）：
- 标普500或纳指日内涨跌幅绝对值 ≥ 1.5%（档位1）或 ≥ 2.5%（档位2）
- VIX单日涨幅 ≥ 15%（档位1）或 ≥ 30%（档位2）
- 抓取到的新闻中出现重大突发关键词（war/attack/crash/bankruptcy等）

## 报告内容质量说明

采用纯脚本关键词匹配 + 数据拼接生成，不经过AI改写，风格偏机械，但完全免费、无额外AI调用成本。

## 修改 GitHub Secrets

```
gh secret set FINNHUB_API_KEY --repo <owner>/<repo> --body "xxx"
gh secret set GMAIL_ADDRESS --repo <owner>/<repo> --body "xxx"
gh secret set GMAIL_APP_PASSWORD --repo <owner>/<repo> --body "xxx"
```

## 手动触发测试

在 GitHub 仓库的 Actions 页面，选择对应 workflow，点击 "Run workflow"，勾选 `force` 可以跳过时间窗口检查直接执行一次（用于验证）。

## 本地手动测试发信

```bash
cd "C:\Users\Admin\Desktop\财经汇报搭建"
python send_email.py --subject "测试标题" --body-file "某个文本文件路径.txt"
```

## 调整触发阈值

幅度阈值写在 `scripts/volatility_alert.py` 的 `magnitude_tier` 函数里；关键词列表在 `scripts/daily_briefing.py` 和 `scripts/volatility_alert.py` 顶部。
