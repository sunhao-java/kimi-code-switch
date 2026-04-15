# kimi-code-switch

一个基于终端 TUI 的 `kimi-code-cli` 配置面板，用来管理 `~/.kimi/config.toml` 里的 `providers`、`models`，并通过 profile 完成多套配置切换，同时支持面板自身的主题、快捷键方案和配置文件路径设置。

当前界面基于 `Textual`，比原始 `curses` 方案更适合做列表、表单和页签切换。

## 设计

- `config.toml` 继续作为 `kimi-code-cli` 的主配置文件，里面保存实际生效的 `providers`、`models` 和当前默认项。
- `config.profiles.toml` 作为 sidecar 文件，保存多套 profile 定义。
- `config.panel.toml` 作为面板 sidecar，保存 TUI 主题、快捷键方案，以及 `kimi-code-cli` 配置文件路径。
- 当你在 TUI 里激活某个 profile 时，工具会把该 profile 的默认值同步写回 `config.toml`。

## 运行

```bash
cd /Users/sunhao/Documents/workspaces/lodsve/kimi-code-switch
python3 run_panel.py
```

或者安装成命令：

```bash
python3 -m pip install -e .
kimi-config-panel
```

项目内已经放了一份本地 `.vendor` 依赖目录，入口会自动加载；如果你要重新安装依赖，也可以执行：

```bash
python3 -m pip install -e .
```

## 键位

- `Left/Right` 或 `h/l`: 切换页签
- `Ctrl+1..6`: 快速切换 `配置档 / 提供方 / 模型 / 预览 / 设置 / 帮助`
- `F7..F9`: 快速聚焦上方 `当前配置档 / 当前生效模型 / 资源概览` 卡片，再按 `Enter` 进入对应列表
- `Tab`: 顶部菜单切换；预览下层标签内切换预览页签；其他场景切到下一项
- `Shift+Tab`: 列表/编辑区回顶部菜单，其他场景回上一项
- `Enter`: 菜单进入列表；预览页进入下层标签；列表进入右侧编辑区
- 方向键：在列表、下拉和输入框内正常移动
- `Ctrl+N`: 当前页新建草稿
- `Ctrl+S`: 保存当前表单
- `Ctrl+D`: 删除当前选中项
- `Ctrl+C`: 在“配置档”页克隆当前配置档为新草稿
- `Ctrl+A`: 在“配置档”页激活当前配置档
- `/` 或 `Ctrl+F`: 聚焦当前列表页搜索框
- `Esc`: 列表页、编辑页、预览区返回顶部菜单；搜索框有内容时先清空搜索
- `F6`: 打开“预览”页，查看将写回的 `config.toml` / `config.profiles.toml` 以及 diff
- `q`: 退出

设置页默认值：

- 主配置文件：`~/.kimi/config.toml`
- 配置档文件：默认跟随主配置目录，指向 `~/.kimi/config.profiles.toml`
- 面板设置文件：`~/.kimi/config.panel.toml`
- TUI 主题：`深海蓝（默认）`
- 快捷键方案：`标准方案（默认）`

## 文件

- 主配置：`~/.kimi/config.toml`
- profile：`~/.kimi/config.profiles.toml`
- 面板设置：`~/.kimi/config.panel.toml`

## Homebrew 发布

项目已经预留了 Homebrew 发布所需的两部分：

- 主仓库内的 GitHub Actions：见 `.github/workflows/release-homebrew.yml`
- 同级 tap 仓库：`../homebrew-kimi-code-switch`

发布链路如下：

1. 在 GitHub 主仓库推送 `vX.Y.Z` tag。
2. Actions 会在 `macos-13` 和 `macos-14` 上构建 `kimi-config-panel` 二进制包。
3. Actions 会把产物上传到对应 GitHub Release。
4. Actions 会渲染 `Formula/kimi-code-switch.rb`，并推送到 GitHub tap 仓库 `sunhao-java/homebrew-kimi-code-switch`。
5. 用户执行 `brew update && brew upgrade` 后即可拉到新版。

### 需要的 GitHub Secrets

- `TAP_GITHUB_TOKEN`
  用于让 GitHub Actions 推送 `sunhao-java/homebrew-kimi-code-switch` 仓库。建议使用 fine-grained PAT，只授予该 tap 仓库的 `Contents: Read and write` 权限。

### 发布前准备

- 在 GitHub 创建仓库 `sunhao-java/homebrew-kimi-code-switch`
- 确保 tap 仓库默认分支已存在，并包含 `Formula/` 目录
- 在 GitHub 主仓库配置好 `TAP_GITHUB_TOKEN`

### tap 仓库命名

按 Homebrew 约定，tap 仓库名使用 `homebrew-<name>`，这里对应：

- 仓库名：`homebrew-kimi-code-switch`
- formula 路径：`Formula/kimi-code-switch.rb`

### 使用 tap 安装

tap 仓库已经切到 GitHub，按 Homebrew 约定使用：

```bash
brew tap sunhao-java/kimi-code-switch
brew install sunhao-java/kimi-code-switch/kimi-code-switch
```

## 说明

- 首次运行如果不存在 profile sidecar，会根据当前 `config.toml` 自动生成一个 `default` profile。
- 配置档的默认模型通过列表选择，不需要手输。
- 模型绑定的提供方通过列表选择，不需要手输。
- 顶部摘要卡支持聚焦后回车直达对应列表。
- 设置页支持修改 `kimi-code-cli` 主配置路径、profile sidecar 路径、TUI 主题和快捷键方案。
- 设置页提供默认值参考，并支持“恢复默认值”“重新载入”“保存设置”。
- 主题目前内置 `深海蓝 / 石墨灰 / 琥珀终端` 三套风格。
- 快捷键方案目前内置 `标准方案` 和 `字母增强`，后者会在标准方案基础上追加一组 `Ctrl+Shift+...` 快捷键。
- 预览页支持先进入下层标签，再切换 `config.toml / 配置 Diff / profiles / 配置档 Diff / 仅看变更`。
- 键盘导航支持“顶部菜单 -> 列表 -> 编辑区”的进入路径，列表页和编辑页都可 `Esc` 回顶部菜单，编辑页也可 `Shift+Tab` 回顶部菜单。
- 列表支持实时搜索过滤，可通过快捷键快速聚焦搜索框、`Esc` 清空搜索，并高亮命中词。
- 预览页提供完整文件、diff，以及“仅看变更”的紧凑视图。
- “仅看变更”会按新增、删除、修改分类展示。
- 保存前可以进入“预览”页查看生成的配置文本和 unified diff。
- 删除 provider 前会检查是否仍被 model 使用。
- 删除 model 前会检查是否仍被 profile 使用。
- `scripts/render_homebrew_formula.py` 用于把 GitHub Release 产物信息渲染成 Homebrew formula，供发布工作流和 tap 仓库复用。
