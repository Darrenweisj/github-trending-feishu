# GitHub 热榜飞书推送

每天自动把 GitHub Trending 热榜发送到飞书群。项目使用 GitHub Actions 运行，不需要让自己的电脑保持开机。

## 推送安排

| 时间 | 推送内容 |
|---|---|
| 每天北京时间 08:10 | GitHub Trending 今日热榜前 10 个项目 |
| 每周一北京时间 08:10 | 今日热榜 + GitHub Trending 本周热榜 |
| 每月 1 日北京时间 08:10 | 今日热榜 + GitHub Trending 本月热榜 |
| 周一恰好是每月 1 日 | 今日、本周、本月三个榜单合并为一条飞书消息 |

榜单直接读取 GitHub Trending 的公开页面，不需要 WorkBuddy Token，也不需要 GitHub Personal Access Token。

## 费用

本项目使用标准 GitHub 托管运行器 ubuntu-latest。在公开仓库中，GitHub 对标准托管运行器提供免费且不限量的使用；本项目没有配置大型运行器或付费服务。

## 配置仓库

1. 在 GitHub 新建一个 **Public（公开）** 仓库，建议命名为 **github-trending-feishu**。
2. 将本项目文件上传到仓库，保留 **.github/workflows/daily.yml** 的目录位置。
3. 打开仓库的 **Settings → Secrets and variables → Actions**，选择 **New repository secret**。
4. 名称填写 **FEISHU_WEBHOOK**，值填写飞书自定义机器人的 Webhook 地址，然后保存。Webhook 是密钥，不要放进代码、README 或公开 Issue。
5. 打开仓库 **Actions**，启用工作流。如果看到工作流运行权限提示，按页面提示启用 Actions。
6. 在 **Actions → Daily GitHub Trending to Feishu → Run workflow** 可以手动触发一次。

手动运行也按运行当天的北京时间决定是否附加周榜或月榜。

## 飞书机器人

在飞书群里添加自定义机器人，并复制它的 Webhook 地址。可以按飞书机器人的安全设置，配置关键词“GitHub热榜”；本项目推送标题包含该关键词。

## 运行说明

- 每天只运行一次；周榜和月榜在对应日期附加到当日消息中。
- 计划时间设置为 Asia/Shanghai 时区的每天 08:10。
- GitHub Actions 的计划运行可能因平台负载延迟几分钟；仓库长期没有提交活动时，计划任务也可能被 GitHub 自动停用。
- 任何榜单抓取失败时，程序会把可用榜单与失败提示发送到飞书，并让该次工作流显示失败，便于查看日志。
- 飞书单条消息有大小限制；需要同时推送多个榜单且内容较长时，程序会自动缩短项目简介。
- 本项目只抓取 GitHub Trending 当前展示的前 10 个项目；榜单内容由 GitHub 页面决定。

## 本地运行（可选）

需要 Python 3.9 或更新版本。先在当前终端设置 FEISHU_WEBHOOK 环境变量，再运行：

    $env:FEISHU_WEBHOOK = "粘贴你的飞书机器人 Webhook"
    python .\github_trending.py

请勿把真实 Webhook 粘贴到公开仓库或提交记录中。

