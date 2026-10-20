# GitHub 热榜飞书推送

这个项目每天从 GitHub Trending 获取热门仓库，并通过飞书自定义机器人发送到群聊。任务运行在 GitHub Actions 上，不依赖本机开机或常驻服务器。

## 功能一览

- 每天推送 GitHub Trending「Today」榜单前 10 个仓库。
- 每周一在同一条消息里附上「This week」周榜。
- 每月 1 日在同一条消息里附上「This month」月榜。
- 周一恰逢每月 1 日时，一条消息包含日榜、周榜和月榜。
- 每个项目显示仓库链接、主要语言、周期新增星数、仓库总星数和简介。
- 可选使用 DeepL API 将项目简介翻译为简体中文；未配置密钥或翻译服务暂时不可用时，仍会发送原文。
- 周期新增星数使用 `+star数字` 格式，例如 `+star1,234`；旁边同时显示累计总星数，例如 `总星数 59,516`。
- 提供 GitHub Actions 手动运行入口，方便首次配置和临时查看。

## 推送时间

工作流每天计划在**北京时间 08:10**启动。日榜每天都有；周榜和月榜按运行当天自动附加。

| 日期 | 消息内容 |
|---|---|
| 周二至周日 | 今日热榜 |
| 周一 | 今日热榜 + 本周热榜 |
| 每月 1 日 | 今日热榜 + 本月热榜 |
| 每月 1 日恰逢周一 | 今日热榜 + 本周热榜 + 本月热榜 |

计划时间由 `.github/workflows/daily.yml` 中的 `schedule` 设置。GitHub Actions 的定时任务可能因平台负载而晚于计划时间送达。

## 飞书消息示例

```text
GitHub热榜 · 2026-10-20
统计日期：2026-10-20（北京时间）
数据来源：GitHub Trending，每个榜单展示前 10 个项目。

今日热榜
1. owner/repo · Python · ⭐ +star1,234 today · 总星数 59,516
   （启用翻译后显示这里的简体中文简介）

本周热榜（仅周一出现）
1. another/repo · Rust · ⭐ +star5,678 this week · 总星数 88,120
   （未配置 DeepL 时显示 GitHub 原始简介）
```

项目名称会链接到对应的 GitHub 仓库。若 GitHub 页面未提供周期新增或累计星数，消息对应位置会显示“未显示”。如果飞书卡片接近消息大小上限，脚本会逐步缩短简介；简介全部省略后仍超限时，本次运行会失败并在 Actions 日志中说明。

## 数据来源和统计口径

脚本读取 GitHub Trending 的公开页面，并分别请求 daily、weekly、monthly 周期页面。每个榜单只保留页面当前展示的前 10 个项目。`+star数字` 取页面中对应周期的新增量（例如 “stars today”）；`总星数` 取同一项目 stargazers 页面的累计 Stars 数。两者口径不同，消息会并列显示，避免把周期新增误认为仓库总星数。

榜单内容由 GitHub 页面决定。若 GitHub 调整页面结构，抓取解析可能需要更新；如果页面暂时不可用，工作流日志会记录失败信息。

## 配置飞书推送

仓库和工作流已经创建。要让自己的飞书群接收消息，需要在 GitHub 仓库保存机器人 Webhook：

1. 在飞书目标群添加自定义机器人，并复制机器人提供的 Webhook 地址。
2. 打开本仓库的 **Settings → Secrets and variables → Actions**。
3. 点击 **New repository secret**。
4. 在 **Name** 中填写 `FEISHU_WEBHOOK`，在 **Secret** 中粘贴 Webhook 地址，然后保存。
5. 打开仓库的 **Actions** 页面；如果 GitHub 提示需要启用工作流，按页面提示启用。
6. 选择 **Daily GitHub Trending to Feishu**，点击 **Run workflow → Run workflow**，启动一次手动运行。
7. 等待运行结束后打开该次运行，确认 `Fetch and send GitHub Trending` 步骤成功，并到飞书群查看消息。

Webhook 是密钥。不要把真实地址写进脚本、README、Issue、截图或提交记录。GitHub Actions 通过 `FEISHU_WEBHOOK` 环境变量读取 Secret；代码和公开仓库文件不包含 Webhook 值。

## 配置简介翻译（可选）

项目使用 DeepL API 的免费接口把简介翻译为简体中文。**不配置这一项也能正常推送热榜**；未配置密钥或翻译失败时，消息会保留 GitHub 上的原始简介。

1. 在 [DeepL for Developers](https://www.deepl.com/en/developers) 注册并创建免费的 **API Developer** 密钥。
2. 复制生成的 API Key。密钥只用于 GitHub Actions 调用 DeepL，不要发到聊天、Issue 或代码文件里。
3. 打开本仓库的 **Settings → Secrets and variables → Actions**，点击 **New repository secret**。
4. 在 **Name** 填写 `DEEPL_API_KEY`，在 **Secret** 粘贴 DeepL API Key，然后保存。
5. 下一次定时运行或手动运行时，简介就会尝试翻译为简体中文。

DeepL 当前为 API Developer 免费方案提供总计 1,000,000 个字符的免费翻译额度；这是总额度，不是每月重置。方案和额度可能调整，请以 [DeepL API 方案说明](https://support.deepl.com/hc/en-us/articles/360021200939-DeepL-API-plans) 为准。脚本会对同一批次重复的简介只请求翻译一次，并且最多发送每条简介前 100 个原文字数，以控制额度消耗。

## 手动运行和查看日志

手动运行适用于首次配置后立即检查，或希望马上获取一条热榜时：

1. 打开仓库 **Actions** 标签页。
2. 在左侧选择 **Daily GitHub Trending to Feishu**。
3. 点击 **Run workflow**，选择 `main` 分支，再点击确认按钮。
4. 打开新生成的运行记录，查看工作流和步骤状态。

手动运行仍根据运行时的北京时间决定是否附加周榜或月榜。例如在周一手动运行也会同时抓取本周榜。

## 常见问题

| 现象 | 检查方法 |
|---|---|
| 没有收到飞书消息 | 先在 Actions 中查看最近运行记录；确认仓库 Secret 名称准确为 `FEISHU_WEBHOOK`，再检查飞书机器人是否仍在目标群、机器人安全设置是否允许消息内容。 |
| Actions 显示缺少 `FEISHU_WEBHOOK` | 在 **Settings → Secrets and variables → Actions** 新建或重新保存同名 Secret。GitHub 不会显示已保存的 Secret 内容，只能重新设置。 |
| 简介仍是英文 | 确认 Actions Secret 名称是 `DEEPL_API_KEY`，不是变量或环境文件；查看运行日志是否提示密钥缺失、DeepL 请求失败或免费额度不足。即使翻译失败，脚本也会继续发送原简介。 |
| 飞书拒绝消息 | 检查 Webhook 是否属于飞书自定义机器人、是否复制完整、机器人是否被停用，以及是否要求消息包含指定关键词。 |
| 热榜抓取失败 | 打开该次 Actions 运行，查看 `Fetch and send GitHub Trending` 步骤日志；可能是网络暂时不可用或 GitHub 页面结构变化。 |
| 日榜成功但周榜/月榜缺失 | 周榜只在北京时间周一生成，月榜只在每月 1 日生成；其他日期不会抓取这两个榜单。 |
| 消息显示 `未显示` 星数 | GitHub Trending 页面没有提供脚本能识别的周期新增星数或累计 Stars 字段。 |
| 运行时间晚于 08:10 | 08:10 是计划触发时间，不是送达保证；GitHub Actions 定时任务可能延迟。可从 Actions 运行记录确认实际开始时间。 |

## 仓库结构

```text
.github/workflows/daily.yml   定时和手动运行配置
github_trending.py            抓榜、生成飞书卡片并推送
.gitignore                    本地临时文件忽略规则
README.md                     项目说明
docs/进度.md                  配置与变更记录
```

`.gitignore` 用于忽略本地 Python 缓存等临时文件。运行工作流不需要额外依赖安装步骤，使用 GitHub Actions 提供的 Python 3.12。

## 本地运行（可选）

需要 Python 3.9 或更新版本。先在 PowerShell 当前窗口设置环境变量，再运行脚本：

```powershell
$env:FEISHU_WEBHOOK = "粘贴你的飞书机器人 Webhook"
# 如果要启用 DeepL 翻译，再设置这一项；不设置时简介按原文发送。
$env:DEEPL_API_KEY = "粘贴你的 DeepL API Key"
python .\github_trending.py
Remove-Item Env:FEISHU_WEBHOOK
Remove-Item Env:DEEPL_API_KEY -ErrorAction SilentlyContinue
```

请只在自己的电脑上输入真实 Webhook 和 DeepL API Key，不要将它们保存进项目文件或提交到 GitHub。脚本运行后会将抓取结果直接发送到该机器人所在的飞书群。

## 运行成本

项目使用 GitHub 托管的 `ubuntu-latest` 标准运行器，不需要购买或维护自己的服务器。GitHub Actions 的免费额度和收费规则可能随账户类型及 GitHub 政策调整，请以仓库所有者 GitHub 账户的 Actions 计费页面为准。

## 已知边界

- 只展示 GitHub Trending 页面前 10 个项目，不保存历史榜单，也不计算自定义排名。
- 榜单数据来自 GitHub Trending 页面；页面不可用或结构变化时，需要查看日志并可能更新解析逻辑。
- GitHub Actions 定时任务可能延迟；仓库长期没有活动时，GitHub 也可能停用计划任务。若任务停止，可在 Actions 页面重新启用。
- DeepL 翻译需要单独创建免费 API Key；密钥缺失、额度用完或服务暂不可用时，简介会回退为 GitHub 原文，其他榜单和飞书推送继续进行。
- 单条飞书消息受机器人消息大小限制。脚本会先缩短简介以尽量保留完整榜单。

