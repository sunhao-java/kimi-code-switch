# AGENTS.md

> 本项目是 `kimi-code-cli` 的配置管理面板，AI 助手在协助开发时需遵循以下约定。

## 项目背景

`kimi-code-switch` 是一个基于终端 TUI 的配置管理工具，用于管理 `kimi-code-cli` 的 `providers`、`models` 和多套 `profile` 配置切换。

### 核心文件

| 文件 | 说明 |
|------|------|
| `src/kimi_code_switch/__init__.py` | 包初始化，负责加载 `.vendor` 本地依赖 |
| `src/kimi_code_switch/__main__.py` | CLI 入口，解析参数并启动 TUI |
| `src/kimi_code_switch/config_store.py` | 配置数据模型和业务逻辑（加载、保存、增删改查） |
| `src/kimi_code_switch/tui.py` | Textual TUI 界面实现（约 1600 行） |
| `src/kimi_code_switch/toml_utils.py` | TOML 序列化工具，保持格式和注释 |

### 外部依赖

- **Textual** (>=8.2,<9): TUI 框架，界面基于其组件系统构建
- **Rich**: 语法高亮和文本渲染

依赖已预装在 `.vendor/` 目录，无需额外安装。

## 配置模型

### 主配置文件 (`~/.kimi/config.toml`)

```toml
default_model = "gpt-4"
default_thinking = true
default_yolo = false

[providers.openai]
type = "openai"
base_url = "https://api.openai.com/v1"
api_key = "sk-..."

[models.gpt4]
provider = "openai"
model = "gpt-4"
max_context_size = 128000
capabilities = ["reasoning"]
```

### Profile Sidecar (`~/.kimi/config.profiles.toml`)

```toml
version = 1
active_profile = "coding"

[profiles.coding]
label = "编程模式"
default_model = "claude-sonnet"
default_thinking = true
```

### 核心数据结构

- `AppState`: 应用状态，包含主配置、profiles、当前激活 profile
- `Profile`: 配置档数据类，包含默认模型、thinking/yolo/主题等设置
- `PROVIDER_KEYS`: provider 字段 (type, base_url, api_key)
- `MODEL_KEYS`: model 字段 (provider, model, max_context_size, capabilities)
- `PROFILE_KEYS`: profile 字段 (default_model, theme, default_thinking 等)

## 编码规范

### Python 版本

- **Python 3.11+**（使用 `tomllib` 标准库）

### 导入顺序

1. `__future__` annotations
2. 标准库（按字母顺序）
3. 第三方库
4. 本地模块

```python
from __future__ import annotations

from pathlib import Path
from typing import Any
import tomllib

from rich.syntax import Syntax
from textual.app import App

from .config_store import AppState
```

### 类型注解

- 使用 Python 3.9+ 内置泛型：`dict[str, Any]`, `list[str]`
- dataclass 使用 `slots=True` 优化内存
- 可选类型使用 `Path | None`（3.10+ 语法）

### TUI 开发约定

1. **CSS 样式**: 使用类级 `CSS` 字符串定义样式
2. **消息传递**: 自定义事件继承 `Message` 类
3. **Bindings**: 键盘快捷键使用 `Binding` 定义
4. **组件 ID**: 使用有意义的 ID 便于测试和调试

```python
class MyWidget(Static):
    CSS = """
    MyWidget { background: #0c1727; }
    """
    
    class Selected(Message):
        def __init__(self, item: str) -> None:
            self.item = item
            super().__init__()
    
    BINDINGS = [Binding("enter", "select", "选择")]
```

## 测试

- 测试文件：`tests/test_config_store.py`
- 使用标准 `unittest` 或 `pytest`
- TUI 测试可使用 Textual 的 `Pilot` 类

## 构建与运行

### 开发运行

```bash
python3 run_panel.py
```

### 安装运行

```bash
python3 -m pip install -e .
kimi-config-panel
```

### 命令行参数

```bash
kimi-config-panel --config ~/.kimi/config.toml --profiles ~/.kimi/config.profiles.toml
```

## 常见修改场景

### 添加新的 Profile 字段

1. 在 `config_store.py` 更新 `PROFILE_KEYS` 常量
2. 在 `Profile` dataclass 添加字段
3. 在 `_profile_from_dict` 和 `bootstrap_profiles` 中处理默认值
4. 在 `tui.py` 的 Profile 编辑表单中添加对应输入控件

### 修改 TUI 样式

- 样式集中在各组件的 `CSS` 字符串中
- 颜色参考：背景 `#071018`, `#0a1624`, `#0c1727`；文字 `#e5edf7`, `#d8e5f2`
- 边框使用 `round #1f3550`

### 添加新的快捷键

- 在对应 Widget 或 App 的 `BINDINGS` 列表中添加
- 实现对应的 `action_xxx` 方法
- 在 Footer 或帮助文本中说明

## 注意事项

1. **状态一致性**: `AppState` 是核心状态，修改后需调用 `save_state()` 持久化
2. **删除保护**: 
   - 删除 provider 前检查是否被 model 引用
   - 删除 model 前检查是否被 profile 引用
   - 不能删除唯一的 profile
   - 不能删除当前激活的 profile
3. **TOML 格式**: 使用自定义的 `toml_utils.py` 保持格式美观（排序、空行）
4. **路径处理**: 统一使用 `pathlib.Path`，支持 `~` 展开
