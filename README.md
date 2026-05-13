# Deep Reading —— 深度阅读 Claude Code 插件

将一本书"读薄"为结构化目录笔记，再将关键概念"读厚"为延伸的概念卡片网络，最终在 Obsidian 中形成知识图谱。

## 核心理念

- **把书读薄**：按原书目录层级建立文件夹结构，每个小节创建阅读笔记骨架，忠实跟随原书框架
- **实体概念沉淀**：将阅读中涌现的关键概念提取为"概念卡片"，卡片之间通过 `[[wikilink]]` 互链，逐步生长为概念网络
- **双向链接**：笔记指向概念，概念指向来源笔记，在 Obsidian 中形成可图谱可视化的知识体系

## 安装

```
/plugin marketplace add moyu12-ae/deep-reading
/plugin install deep-reading@deep-reading-marketplace
```

## 使用方式

### 初始化一本书

```
初始化《xxx》
```

插件会自动：
1. 从 epub/md 文件提取章节目录
2. 创建与原书层级一致的文件夹结构
3. 为每个小节生成阅读笔记骨架（含摘要、要点、摘录、批注区）
4. 创建 `实体概念/` 文件夹
5. 生成 `_目录.md` 导航文件（含 pandoc 行号定位）
6. 在工作区 `CLAUDE.md` 中注册书籍条目

### 做阅读笔记

```
阅读《xxx》第一章的"xxx"小节
```

插件会通过 pandoc 按行号定位原文内容，并在对应的小节笔记中填充摘要、关键要点、原文摘录等内容。

### 创建概念卡片

```
创建概念卡片 xxx
```

在 `实体概念/` 下生成概念卡片文件，包含核心定义、详细展开、延伸方向等区域。

### 同步工作区

```
同步工作区
```

触发 `sync-workspace` skill，扫描所有书籍的实际状态，与 CLAUDE.md 对比并修复不一致。

## 自动同步

每次对话结束（Stop hook）时自动执行：

- **auto-sync.py**：扫描每本书的阅读进度（unread/reading/completed）和实体概念数量，更新 CLAUDE.md 中的 `<!-- SYNC:BOOK:... -->` 块
- **check-consistency.py**：检查概念卡片的 source 指向和笔记中的 wikilink 目标是否存在，报告断链

## 与 Obsidian 集成

插件产出的所有文件都是标准 Markdown + wikilink + YAML frontmatter。用 Obsidian 打开工作区文件夹作为 Vault 即可获得：

- **Graph View**：自动展示概念网络图谱
- **Backlinks 面板**：查看所有引用当前文件的其他文件
- **标签导航**：通过 `tags` frontmatter 筛选阅读笔记 vs 实体概念

## 工作区结构示例

```
<工作区>/
├── CLAUDE.md                  # 工作区索引（含 SYNC 同步块）
├── 《书A》/
│   ├── _目录.md                # 导航文件（含 pandoc 行号）
│   ├── 第一编-xxx/
│   │   └── 第一章-xxx/
│   │       ├── 小节1.md        # 阅读笔记
│   │       └── 小节2.md
│   └── 实体概念/
│       ├── 概念A.md            # 概念卡片
│       └── 概念B.md
└── 《书B》/
    ├── _目录.md
    ├── ...
    └── 实体概念/
```

## 依赖

- **pandoc**：用于 epub 格式转换和内容定位（`brew install pandoc`）
- **Obsidian**（可选）：用于知识图谱可视化
- Python 3 标准库（auto-sync.py / check-consistency.py 零第三方依赖）

## 许可证

MIT
