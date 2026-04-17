# Changelog

本文档按仓库 tag 记录版本变化。

## v1.0.7

发布时间点：tag `v1.0.7`

主要变化：
- 优化关于弹框主题，使其与整体风格保持一致
- 修复关于弹框关闭按钮的视觉边框问题
- 增强顶部摘要区、tab 页、编辑区与预览区之间的焦点导航
- 首次进入应用时默认聚焦顶部第一个摘要卡
- 调整关于弹框字段文案，将“英文名”改为“作者”

关联提交：
- `f50f825` `feat: 优化弹框主题与焦点导航交互`
- `31e9122` `Implement feature X to enhance user experience and fix bug Y in module Z`

## v1.0.6

发布时间点：tag `v1.0.6`

主要变化：
- 统一入口程序名称为 `kimi-code-switch`
- 根目录开发入口改为 `kimi-code-switch.py`
- 同步更新打包、文档与 Homebrew 相关命名

关联提交：
- `5e6f1c5` `feat: 统一入口程序名称为 kimi-code-switch`

## v1.0.5

发布时间点：tag `v1.0.5`

主要变化：
- 统一命令名为 `kimi-config-switch`
- 兼容 Python `3.9+`
- 引入 `tomllib / tomli` 兼容层
- 强化配置保存的原子写入与校验逻辑
- 补充关于弹框、摘要卡导航、模型命名规则等测试

关联提交：
- `1c6001c` `feat: 统一 kimi-config-switch 命令并兼容 Python 3.9`

## v1.0.4

发布时间点：tag `v1.0.4`

主要变化：
- 新增关于弹框
- 支持展示作者信息与当前版本号

关联提交：
- `52ababb` `feat: 新增关于弹框与版本信息展示`

## v1.0.3

发布时间点：tag `v1.0.3`

主要变化：
- 优化首次配置时的依赖禁用逻辑
- 改善空配置或依赖未准备完成时的交互体验

关联提交：
- `7a4f82f` `fix: 优化首次配置时的依赖禁用逻辑`

## v1.0.2

发布时间点：tag `v1.0.2`

主要变化：
- 优化配置档默认模型不存在时的错误提示
- 提供更明确的模型 key 引导

关联提交：
- `ab823ec` `fix: 优化配置档默认模型不存在时的错误提示`

## v1.0.1

发布时间点：tag `v1.0.1`

主要变化：
- 修复 Homebrew 发布包中缺失 `Textual` 模块的问题

关联提交：
- `3949870` `fix: 修复 Homebrew 发布包缺失 Textual 模块问题`

## v1.0.0

发布时间点：tag `v1.0.0`

主要变化：
- 建立 Homebrew tap 发布流程
- 新增设置页，并支持面板配置持久化
- 调整 GitHub Actions 的 macOS runner 配置
- 初始化首个可用的 TUI 配置面板版本

关联提交：
- `c8fa6b8` `fix: 更新 GitHub Actions 的 macOS runner 配置`
- `eb02175` `chore: 切换 Homebrew tap 发布到 GitHub 仓库`
- `8dbc043` `feat: 增加 Homebrew tap 发布流程`
- `8e0cc8e` `feat: 增加设置页并支持面板配置持久化`
