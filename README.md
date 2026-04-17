# kimi-code-switch

`kimi-code-switch` 是一个基于 `Textual` 的终端配置面板，用于管理 `kimi-code-cli` 的主配置、模型、提供方和多套 `Profile`。

它面向这些场景：
- 维护 `~/.kimi/config.toml` 中的 `providers`、`models` 和默认项
- 用 `config.profiles.toml` 管理多套配置组合，并一键切换
- 独立保存面板自己的主题、快捷键方案和配置文件路径

## 功能概览

- 维护 `providers / models / Profile`
- 激活 `Profile` 时自动把默认值写回 `config.toml`
- 支持预览 `config.toml`、`config.profiles.toml` 和对应 diff
- 支持面板主题、快捷键方案、配置路径持久化
- 支持 Homebrew 发布与独立二进制分发

## 配置文件

- 主配置：`~/.kimi/config.toml`
- Profile sidecar：`~/.kimi/config.profiles.toml`
- 面板设置：`~/.kimi/config.panel.toml`

职责划分如下：
- `config.toml`：当前实际生效的 `providers`、`models`、默认模型和默认开关
- `config.profiles.toml`：多套 `Profile` 定义
- `config.panel.toml`：面板主题、快捷键方案、配置路径

## 安装与运行

项目支持 Python `3.9+`。

开发运行：

```bash
cd /Users/sunhao/Documents/tools/kimi-code-switch
python3 kimi-code-switch.py
```

安装为命令：

```bash
python3 -m pip install .
kimi-code-switch
```

如果本地是较老的 `pip`，建议先升级：

```bash
python3 -m pip install --upgrade pip setuptools wheel
python3 -m pip install .
```

## 核心交互

- `Ctrl+1..6`：切换 `配置Profile / 提供方 / 模型 / 预览 / 设置 / 帮助`
- `F7..F9`：聚焦顶部摘要卡
- `F10`：打开“关于”弹框
- `Enter`：进入下一级区域
- `Esc`：按层级返回
- `Tab / Shift+Tab`：在同一水平操作行内切换
- `/` 或 `Ctrl+F`：聚焦搜索框
- `Ctrl+N`：新建草稿
- `Ctrl+S`：保存
- `Ctrl+D`：删除
- `Ctrl+C`：克隆当前 `Profile`
- `Ctrl+A`：激活当前 `Profile`
- `F6`：打开预览
- `q`：退出

当前焦点层级大致为：
- 顶部摘要卡
- 主 tab 页
- 左侧列表
- 右侧编辑区
- 预览子页签 / 预览内容

## 使用说明

- 首次运行如果不存在 `config.profiles.toml`，会自动生成一个 `default` Profile
- `Profile` 的默认模型通过下拉选择，不需要手输
- 模型的提供方通过下拉选择，模型名输入框只填写不含提供方前缀的后缀
- 删除提供方前会检查是否仍被模型引用
- 删除模型前会检查是否仍被 `Profile` 或当前默认模型引用
- 保存前可以先进入预览页查看生成结果和 diff

## 内置主题

- 深海蓝（默认）
- 石墨灰
- 琥珀终端

## Homebrew 发布

仓库已内置 Homebrew 发布流程：

- GitHub Actions 工作流：`.github/workflows/release-homebrew.yml`
- tap 仓库：`sunhao-java/homebrew-kimi-code-switch`
- formula 路径：`Formula/kimi-code-switch.rb`

发布流程：

1. 推送 `vX.Y.Z` tag
2. Actions 构建 macOS `amd64 / arm64` 二进制
3. 上传 GitHub Release 产物
4. 渲染并推送 Homebrew formula

使用方式：

```bash
brew tap sunhaojava/kimi-code-switch git@github.com:sunhao-java/homebrew-kimi-code-switch.git
brew install kimi-code-switch
kimi-code-switch
```

## 开发说明

- 入口脚本：`kimi-code-switch.py`
- CLI 入口：`src/kimi_code_switch/__main__.py`
- 状态与持久化：`src/kimi_code_switch/config_store.py`
- 面板设置：`src/kimi_code_switch/panel_settings.py`
- TUI 主界面：`src/kimi_code_switch/tui.py`
- TOML 输出：`src/kimi_code_switch/toml_utils.py`

运行测试：

```bash
python3 -m unittest tests.test_config_store
```

版本历史见 [CHANGELOG.md](/Users/sunhao/Documents/tools/kimi-code-switch/CHANGELOG.md)。
