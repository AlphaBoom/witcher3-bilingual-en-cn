# The Witcher 3 — English / 简体中文

本地生成的英文优先双语文本工具，面向 Windows DX12、Remastered v5 的 v164 UTF-8 语言文件。

- 对话字幕英文在上、中文在下；任务和物品说明保留双语。
- 菜单 UI 使用英文，包含主标签、Glossary 子标签、按钮和筛选提示。
- Remove Upgrade 列表里的符文／升级名称使用英文；背包名称保持双语。
- 动态 `$I$` / `$F$` / `$S$` 参数由配套脚本分别填入两种语言。
- 按实际语音、journal 引用和 HTML 标记选择换行；未知字段使用 ` / `。

仓库只保存工具、规则和自有脚本模板。原版游戏文本、生成文件、备份、设置和存档均不上传；从自己的本地安装生成。

## 使用

需要 Windows PowerShell、Python 3.10+，无第三方 Python 依赖。先关闭游戏，在本仓库目录运行。路径示例需替换为自己的游戏目录。

```powershell
python src/maintain.py check --game-dir "D:\Games\The Witcher 3"
python src/maintain.py update --game-dir "D:\Games\The Witcher 3"
python src/maintain.py install --game-dir "D:\Games\The Witcher 3"
```

第二条命令只生成和验证。也可以一步生成、验证并安装：

```powershell
python src/maintain.py update --game-dir "D:\Games\The Witcher 3" --install
```

安装到受保护目录时使用管理员终端。默认通过系统 Documents 文件夹定位 `The Witcher 3/dx12user.settings`；特殊路径可传 `--settings-path`。安装把文本语言设为 CN 以启用中文字体，保留语音设置；游戏内应选 English 语音、简体中文文本并开启字幕。

工作目录位于游戏的 `_bilingual_en_cn`，保存原文件、报告及回滚副本。Steam 更新覆盖语言文件后，重新运行 update 即可按新版本生成，不能直接覆盖旧的生成文件。若仅更新了可执行文件、旧双语文件还在，工具会停止，先通过 Steam 恢复当前原版语言文件。

还原当前版本的原始中文文件和原先文本语言设置：

```powershell
python src/maintain.py restore --game-dir "D:\Games\The Witcher 3"
```

检测到未知修改、备份损坏、版本变化、未匹配的占位符或脚本签名时会停止，请检查而非绕过校验。还原也有哈希保护，不会强行覆盖其他修改。

## 维护

- `src/menu_english_keys.json`：英文 UI 查询键；扫描 Flash 和菜单脚本后与已有规则合并。
- `src/placeholder_rules.py`：双语参数处理及少量原版中文参数修正。
- `src/rendering_rules.py`：字幕、journal 和换行分类。
- `scripts/`：自有 WitcherScript 模板。59 种升级物品的英文名称从本地 XML 和英文文件生成，不写死在仓库。
- `src/validate_release.py`：文本、键、参数、升级名称及包装函数签名校验，不依赖旧备份历史。

当前数据验证基线：游戏 **5.0.0.1090142**（2026-10-29），766 个英文 UI 查询键、372 条动态双语文本、59 种升级物品。自动检查不等同于真实游戏脚本编译和排版验证；发布兼容版本前还应实际进入游戏检查对话、技能数值、菜单及 Remove Upgrade。

```powershell
python -m unittest discover -s tests -v
```

反馈问题时附游戏版本、错误文本、界面截图及 `release-validation.json`；不要上传完整游戏资源、设置或存档。

本项目与 CD PROJEKT RED 无隶属关系。文件格式实现参考链接见对应 Python 文件头部。
