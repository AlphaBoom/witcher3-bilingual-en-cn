# witcher3-bilingual-en-cn

为《巫师 3：狂猎》次世代版（v5）生成英文 + 简体中文双语文本。英文在前，中文在后，语音保持英文。

- 对话字幕：英文、中文各一行
- 任务、人物、怪物、物品说明：英文段落后接中文段落
- 任务标题、物品名称等短文本：`English / 中文`
- 菜单按钮、分页、筛选、按键提示，以及 Remove Upgrade 页面的升级名称：仅英文

工具在本地读取当前游戏文件生成双语文本，不附带任何游戏资源。

## 环境要求

- Windows，游戏 DX12 版本（`bin\x64_dx12\witcher3.exe`）
- Python 3.10 或更新版本，无第三方依赖

最近一次验证的游戏版本：5.0.0.1090142（2026-10-29）。

## 安装

1. 安装 [Python](https://www.python.org/downloads/windows/)，安装时勾选 “Add python.exe to PATH”。
2. 下载 [项目 ZIP](https://github.com/AlphaBoom/witcher3-bilingual-en-cn/archive/refs/heads/main.zip) 并解压。
3. 关闭游戏，运行 `install.cmd`。

   脚本会在 Steam 库和 GOG 安装位置中查找游戏目录，并在开始前请求确认。未找到时，按提示输入或拖入游戏目录（包含 `bin` 和 `content` 的文件夹）。所选目录会保存到 `game-dir.txt`，下次运行直接使用。

4. 在游戏中设置 选项 → 语言：语音 `English`，文本 `简体中文`，字幕开启。

   文本语言需选择简体中文，双语内容使用中文语言槽和字体。安装脚本会自动修改该设置。

## 游戏更新后

游戏更新可能覆盖语言文件，导致双语失效。此时直接重新运行 `install.cmd` 即可，无需更新本工具。

只有以下情况需要下载本项目的新版本：

- 生成或校验阶段报错，例如语言文件格式不受支持、脚本函数签名不匹配
- 菜单中出现新的按钮或标签显示为双语（新增的 UI 文本尚未加入英文规则）

如果提示游戏已更新但旧的双语文件仍在，说明更新没有覆盖语言文件。先在 Steam 中验证游戏文件完整性，再运行 `install.cmd`。

## 检查与卸载

| 脚本 | 作用 |
| --- | --- |
| `check.cmd` | 检查安装状态，以及双语文件是否与当前游戏版本匹配 |
| `restore.cmd` | 还原原版中文文本和原文本语言设置，并移除配套脚本 |

运行前请关闭游戏。游戏目录下的 `_bilingual_en_cn` 文件夹保存了原始文件备份，还原时需要使用，请勿删除。

## 修改的文件

| 文件 | 修改内容 |
| --- | --- |
| `content\content0\cn.w3strings` | 替换为双语文本 |
| `mods\modBilingualEnCnPlaceholders\` | 配套脚本，将动态数值同时填入英文和中文部分 |
| `文档\The Witcher 3\dx12user.settings` | `TextLanguage`、`RequestedTextLanguage` 设为 `CN` |

安装前会备份并逐项校验，任一步骤失败都会回滚。不修改音频、贴图和 bundle 文件。

## 常见问题

| 提示 | 处理 |
| --- | --- |
| 没有找到 Python | 安装 Python 3.10+ 并确认已加入 PATH |
| 这个文件夹不是游戏目录 | 应选择包含 `bin` 和 `content` 的游戏根目录 |
| 游戏正在运行 | 完全退出游戏和启动器后重试 |
| 拒绝访问 / Access denied | 以管理员身份运行 `install.cmd` |
| 游戏已更新，但旧的双语文件仍在 | 在 Steam 中验证游戏文件完整性，再运行 `install.cmd` |
| 校验失败、参数不匹配、启动时脚本编译错误 | 下载最新版本重试；仍有问题请提交 [Issue](https://github.com/AlphaBoom/witcher3-bilingual-en-cn/issues) |

提交 Issue 时请附上游戏版本、窗口中的完整输出和相关截图，如有可附上 `_bilingual_en_cn\release-validation.json`。无需上传游戏文件或存档。

## 命令行用法

`.cmd` 脚本最终调用 `src\maintain.py`，也可以直接使用：

```powershell
python .\src\maintain.py update  --game-dir "<游戏目录>" --install   # 生成、校验并安装
python .\src\maintain.py update  --game-dir "<游戏目录>"             # 仅生成和校验
python .\src\maintain.py install --game-dir "<游戏目录>"             # 安装已生成的文件
python .\src\maintain.py check   --game-dir "<游戏目录>"             # 检查状态
python .\src\maintain.py restore --game-dir "<游戏目录>"             # 还原
```

设置文件不在默认位置时，添加 `--settings-path "<路径>\dx12user.settings"`。

## 开发

仓库只包含工具、规则和脚本模板。原版游戏资源、生成文件、备份和个人设置只保存在本地。

| 文件 | 用途 |
| --- | --- |
| `install.cmd` / `check.cmd` / `restore.cmd` | 双击入口，调用 `launcher.ps1` |
| `launcher.ps1` | 查找 Python 和游戏目录，调用 `maintain.py` |
| `src/maintain.py` | 检查、更新、安装、还原入口 |
| `src/menu_english_keys.json` | 显示为英文的 UI 查询键，扫描菜单资源后与已有规则合并 |
| `src/placeholder_rules.py` | 双语动态参数处理，以及少量原版中文参数修正 |
| `src/rendering_rules.py` | 根据语音索引、journal 引用和 HTML 标记选择换行方式 |
| `src/validate_release.py` | 校验文本、查询键、参数、升级名称和包装函数签名 |
| `scripts/` | WitcherScript 模板，升级物品名称从本地游戏文件生成 |

运行测试：

```powershell
python -m unittest discover -s tests -v
```

当前基线：766 个英文 UI 查询键、372 条动态双语文本、59 种升级物品。适配新游戏版本时，除自动校验外，还需在游戏内检查对话、技能数值、菜单和 Remove Upgrade 页面。

本项目与 CD PROJEKT RED 无隶属关系。文件格式实现的参考链接见对应 Python 文件头部。
