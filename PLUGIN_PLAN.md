# 深度阅读 → Claude Code 插件完整方案（改进版）

## 一、插件架构总览

```
deep-reading/
├── .claude-plugin/
│   └── plugin.json                  # 插件元信息 + hooks 配置
├── skills/
│   ├── deep-reading/
│   │   └── SKILL.md                 # 核心 skill（含 1.6 自动同步指令）
│   └── sync-workspace/
│       └── SKILL.md                 # /sync-workspace 主动同步
└── hooks/
    ├── hooks.json                   # Stop hook 配置
    └── scripts/
        ├── auto-sync.py             # Stop hook：数字字段自动同步
        └── check-consistency.py     # 双向链接一致性检查
```

**相比旧版变更**：
- 删除了 `commands/` 目录（5个 command 的功能已在 SKILL.md 中覆盖，或合并为独立 skill）
- 删除了 `agents/` 目录（同步检查 agent 冗余，逻辑已覆盖）
- 精简为 7 个文件，结构更清晰

## 二、plugin.json

```json
{
  "name": "deep-reading",
  "version": "1.0.0",
  "description": "深度阅读工作区管理——将书籍读薄为结构化笔记，再将关键概念读厚为延伸的概念卡片网络，在 Obsidian 中形成知识图谱。自动同步工作区 CLAUDE.md 与书籍文件夹的阅读进度和概念数量。",
  "author": {
    "name": "moyu12-ae"
  },
  "license": "MIT",
  "keywords": ["reading", "obsidian", "knowledge-graph", "notes", "deep-reading"],
  "hooks": {
    "Stop": [
      {
        "matcher": ".*",
        "hooks": [
          {
            "type": "command",
            "command": "python3 ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/auto-sync.py",
            "description": "Stop hook: auto-sync CLAUDE.md reading progress and concept counts",
            "timeout": 30000,
            "continueOnError": true
          }
        ]
      }
    ]
  }
}
```

## 三、同步机制设计

### 3.1 同步什么

CLAUDE.md 中每本书有 6 个字段，其中 2 个自动计算、2 个 AI 维护、2 个手动维护：

| 字段 | 维护方式 | 说明 |
|------|:------:|------|
| 路径 | 手动 | 初始化时写入 |
| 作者 | 手动 | 从 _目录.md 读取 |
| 类型 | 手动 | 初始化时写入 |
| 说明 | 手动 | 初始化时写入 |
| **阅读进度** | **脚本自动** | Stop hook 统计数字 |
| **阅读状态** | **AI 维护** | 语义描述，AI 推断 |
| **实体概念数** | **脚本自动** | Stop hook 文件计数 |

### 3.2 CLAUDE.md 书籍条目新模板

```markdown
### 《写作技法荟萃》
<!-- SYNC:BOOK:写作技法荟萃 -->
- **路径**：`写作技法荟萃/`
- **作者**：李志义、邢维
- **类型**：写作技法辞典
- **说明**：涵盖立意、描写、叙述、结构、修辞、整体六大类写作技法的工具书
- **阅读进度**：15个小节中 0个已完成，0个进行中，15个未读
- **阅读状态**：未开始
- **实体概念数**：0
<!-- SYNC:END -->
```

`<!-- SYNC:BOOK:书名 -->` 和 `<!-- SYNC:END -->` 是不可见标记，让 auto-sync.py 精确匹配和替换同步块，避免脆弱的自然语言正则。

### 3.3 两层同步架构

**脚本层**（Stop hook → auto-sync.py）：
- 时机：每次对话结束自动触发
- 能力：文件计数、数字字段更新、断链检测
- 限制：不做语义判断，只做确定性操作
- 失败安全：`continueOnError: true`，不影响正常使用

**AI 层**（SKILL.md 1.6 节）：
- 时机：执行阅读笔记/创建概念卡片/更新延伸方向后
- 能力：语义描述推断、双向链接交叉验证、跨书关联发现
- 依赖：AI 的理解力和上下文

两层互补，互不依赖。

### 3.4 主动同步（/sync-workspace）

`skills/sync-workspace/SKILL.md` 实现，用户主动触发：

1. 扫描每本书的文件系统状态
2. 对比 CLAUDE.md 中的记录
3. 列出所有不一致（数字偏差、缺失条目、断链）
4. 逐一修复，输出同步报告

## 四、文件详细设计

### 4.1 skills/deep-reading/SKILL.md（增量修改）

在现有 SKILL.md 基础上做两处修改：

**修改一**：CLAUDE.md 书籍条目模板（1.1 节第五步）——增加 SYNC 标记和阅读状态字段

旧模板：
```markdown
### <书名>
- **路径**：`<书名>/`
- **作者**：<作者>
- **类型**：<教材/专著/辞典等>
- **说明**：<一句话描述>
- **阅读进度**：未开始
- **实体概念数**：0
```

新模板：
```markdown
### <书名>
<!-- SYNC:BOOK:<书名> -->
- **路径**：`<书名>/`
- **作者**：<作者>
- **类型**：<教材/专著/辞典等>
- **说明**：<一句话描述>
- **阅读进度**：0个小节中 0个已完成，0个进行中，0个未读
- **阅读状态**：未开始
- **实体概念数**：0
<!-- SYNC:END -->
```

**修改二**：在 1.5 节之后新增 1.6 节

```markdown
### 1.6 自动同步到 CLAUDE.md

每次完成以下操作后，自动更新 CLAUDE.md 中对应书籍的同步块：

**更新阅读进度统计**：
- 扫描该书中所有小节 .md 文件的 `status` frontmatter
- 统计 unread / reading / completed 数量
- 更新 SYNC 块中的"阅读进度"

**更新实体概念数**：
- 统计 `实体概念/` 下的 .md 文件数量
- 更新 SYNC 块中的"实体概念数"

**更新阅读状态**（语义描述）：
- 根据阅读进度统计和最后一次操作推断并更新"阅读状态"
- 全部 unread → "未开始"
- 有 completed 且已完成某完整章节 → "已完成XX章"
- 有 reading/completed 但无规律 → "正在阅读"

## 同步两层架构

深度阅读的同步分为两个独立层，互补而不依赖：

1. **脚本层**（Stop hook → auto-sync.py）：对话结束时自动触发，做文件计数和数字字段更新。轻量、可靠、不消耗 token。
2. **AI 层**（Skill 1.6 节）：在每次阅读笔记/概念卡片操作后，由 AI 做语义判断和交叉验证。

脚本层失败不影响 AI 层工作（`continueOnError: true`）。
```

### 4.2 skills/sync-workspace/SKILL.md

```markdown
---
name: sync-workspace
description: 主动同步深度阅读工作区——扫描所有书籍的实际状态，与 CLAUDE.md 对比，列出不一致并修复。当用户说"同步工作区""检查同步状态""sync workspace"时触发。
---

# 主动同步工作区

扫描工作区中每本书的实际文件状态，与 CLAUDE.md 对比，报告并修复所有不一致。

## 扫描内容

### 数字字段（精确对比）
- 阅读进度统计（小节 status 分布）
- 实体概念数量（实体概念/ .md 文件数）

### 语义字段（提示但不自动修改）
- 阅读状态描述（由 AI 推断后建议更新）
- 书籍说明（仅当明显过时时提示）

### 双向链接完整性
- 每个概念卡片的 `source` frontmatter 指向的笔记文件是否存在
- 已读笔记中"本节概念"区的 wikilink 目标概念卡片是否存在

## 执行流程

1. 读取 CLAUDE.md，定位每本书的 `<!-- SYNC:BOOK:... -->` 块，解析记录值
2. 对每本书：
   a. 确认文件夹存在
   b. 遍历所有非实体概念、非 _ 开头的 .md 文件，解析 frontmatter 的 `status`，统计分布
   c. 统计 `实体概念/` 下 .md 文件数
   d. 运行 check-consistency.py（如果存在）或手动检查双向链接
3. 逐书对比，生成不一致清单
4. 对数字不一致：直接更新 CLAUDE.md 中的 SYNC 块
5. 对语义不一致：列出建议，请用户确认后更新
6. 对断链：列出问题，请用户确认后修复
7. 输出同步报告

## 同步报告格式

```markdown
# 深度阅读工作区同步报告

## 《写作技法荟萃》
| 字段 | 记录值 | 实际值 | 状态 |
|------|--------|--------|:----:|
| 阅读进度 | 15中5/3/7 | 15中5/3/7 | ✓ |
| 实体概念数 | 3 | 5 | ✗ 已更新 |
| 阅读状态 | 正在阅读立意技法 | — | ✓ |

### 双向链接
- ✗ 实体概念/画龙点睛.md → [[立意技法/片言居要]]（概念卡片不存在）
- ✓ 其余链接正常

## 建议
- 阅读状态可从"正在阅读立意技法"更新为"立意技法已完成，正在阅读描写技法"
```
```

### 4.3 hooks/hooks.json

```json
{
  "hooks": {
    "Stop": [
      {
        "matcher": ".*",
        "hooks": [
          {
            "type": "command",
            "command": "python3 ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/auto-sync.py",
            "description": "Auto-sync CLAUDE.md reading progress and concept counts",
            "timeout": 30000,
            "continueOnError": true
          },
          {
            "type": "command",
            "command": "python3 ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/check-consistency.py",
            "description": "Check bidirectional link consistency silently",
            "timeout": 30000,
            "continueOnError": true
          },
          {
            "type": "command",
            "command": "python3 ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/check-consistency.py",
            "description": "Check bidirectional link consistency silently",
            "timeout": 30000,
            "continueOnError": true
          }
        ]
      }
    ]
  }
}
```

### 4.4 hooks/scripts/auto-sync.py

```python
#!/usr/bin/env python3
"""
自动同步脚本（Stop hook 触发）。
扫描工作区每本书的阅读进度和概念数量，更新 CLAUDE.md 中的 SYNC 块。
只做文件计数和精确文本替换，不做 AI 语义判断。
"""
import os
import re
import yaml
from pathlib import Path


def count_statuses(book_path):
    """统计一本书中所有小节的 status 分布"""
    counts = {"unread": 0, "reading": 0, "completed": 0}
    for md_file in Path(book_path).rglob("*.md"):
        # 跳过实体概念文件夹、_开头的导航文件
        if "实体概念" in str(md_file) or md_file.name.startswith("_"):
            continue
        try:
            content = md_file.read_text()
            if content.startswith("---"):
                fm_end = content.find("---", 3)
                if fm_end > 0:
                    fm = yaml.safe_load(content[3:fm_end])
                    if isinstance(fm, dict):
                        status = fm.get("status", "unread")
                        if status in counts:
                            counts[status] += 1
        except Exception:
            pass
    return counts


def count_concepts(book_path):
    """统计实体概念数量"""
    concepts_dir = Path(book_path) / "实体概念"
    if not concepts_dir.exists():
        return 0
    return len([f for f in concepts_dir.glob("*.md")])


def find_books(workspace_path):
    """找出工作区中的所有书籍文件夹（包含 _目录.md 或 实体概念/）"""
    books = []
    for entry in sorted(os.listdir(workspace_path)):
        entry_path = os.path.join(workspace_path, entry)
        if not os.path.isdir(entry_path) or entry.startswith("."):
            continue
        has_index = os.path.exists(os.path.join(entry_path, "_目录.md"))
        has_concepts = os.path.exists(os.path.join(entry_path, "实体概念"))
        if has_index or has_concepts:
            books.append(entry)
    return books


def update_sync_block(claude_content, book_name, progress_str, concept_count):
    """更新 CLAUDE.md 中指定书籍的 SYNC 块"""
    pattern = re.compile(
        rf'(<!-- SYNC:BOOK:{re.escape(book_name)} -->\n.*?)'
        rf'(-\*\*阅读进度\*\*[：:]\s*).*?(\n)'
        rf'(.*?-\*\*实体概念数\*\*[：:]\s*)\d+',
        re.DOTALL
    )
    
    def replacer(m):
        return (
            m.group(1)
            + m.group(2) + progress_str + m.group(3)
            + m.group(4) + str(concept_count)
        )
    
    return pattern.sub(replacer, claude_content)


def main():
    workspace = os.environ.get("CLAUDE_WORKSPACE")
    if not workspace:
        workspace = os.getcwd()
    
    claude_path = os.path.join(workspace, "CLAUDE.md")
    if not os.path.exists(claude_path):
        return
    
    books = find_books(workspace)
    if not books:
        return
    
    with open(claude_path, "r") as f:
        content = f.read()
    
    updated_content = content
    for book_name in books:
        book_path = os.path.join(workspace, book_name)
        
        # 检查 SYNC 块是否存在
        if f"SYNC:BOOK:{book_name}" not in content:
            continue
        
        counts = count_statuses(book_path)
        total = sum(counts.values())
        if total == 0:
            continue
        
        progress_str = f"{total}个小节中 {counts['completed']}个已完成，{counts['reading']}个进行中，{counts['unread']}个未读"
        concept_count = count_concepts(book_path)
        
        updated_content = update_sync_block(
            updated_content, book_name, progress_str, concept_count
        )
    
    if updated_content != content:
        with open(claude_path, "w") as f:
            f.write(updated_content)
        print(f"[auto-sync] CLAUDE.md updated")


if __name__ == "__main__":
    main()
```

### 4.5 hooks/scripts/check-consistency.py

```python
#!/usr/bin/env python3
"""
双向链接一致性检查。
检查概念卡片的 source 指向的笔记文件是否存在，
以及笔记中"本节概念"的 wikilink 目标概念卡片是否存在。
"""
import os
import re
import yaml
from pathlib import Path


def extract_wikilinks(text):
    """提取所有 [[目标|别名]] 或 [[目标]] 中的目标文件名"""
    links = re.findall(r'\[\[(.*?)(?:\|.*?)?\]\]', text)
    targets = []
    for link in links:
        # 取路径最后一段作为文件名
        name = link.strip().split("/")[-1]
        targets.append(name)
    return targets


def parse_frontmatter(content):
    """解析 YAML frontmatter"""
    if not content.startswith("---"):
        return {}
    fm_end = content.find("---", 3)
    if fm_end > 0:
        try:
            return yaml.safe_load(content[3:fm_end]) or {}
        except Exception:
            return {}
    return {}


def check_book(book_path):
    """检查一本书的双向链接一致性，返回问题列表"""
    issues = []
    concepts_dir = Path(book_path) / "实体概念"
    
    if not concepts_dir.exists():
        return issues
    
    # 构建笔记文件索引：文件名（不含扩展名）→ 相对路径
    note_index = {}
    for md_file in Path(book_path).rglob("*.md"):
        if "实体概念" in str(md_file) or md_file.name.startswith("_"):
            continue
        rel_path = str(md_file.relative_to(book_path))
        note_index[md_file.stem] = rel_path
    
    # 检查概念卡片的 source 指向
    for concept_file in concepts_dir.glob("*.md"):
        content = concept_file.read_text()
        fm = parse_frontmatter(content)
        
        sources = fm.get("source", [])
        if isinstance(sources, str):
            sources = [sources]
        for source in sources:
            targets = extract_wikilinks(source)
            for target in targets:
                if target not in note_index:
                    issues.append(
                        f"断链：实体概念/{concept_file.name} → {target}（笔记不存在）"
                    )
    
    # 检查已读笔记中"本节概念"的 wikilink 目标
    for md_file in Path(book_path).rglob("*.md"):
        if "实体概念" in str(md_file) or md_file.name.startswith("_"):
            continue
        content = md_file.read_text()
        fm = parse_frontmatter(content)
        
        # 只检查已读的笔记
        if fm.get("status") == "unread":
            continue
        
        # 提取"本节概念"区
        match = re.search(
            r'## 本节概念\s*\n(.*?)(?=\n## |\Z)', content, re.DOTALL
        )
        if match:
            targets = extract_wikilinks(match.group(1))
            for target in targets:
                concept_path = concepts_dir / f"{target}.md"
                if not concept_path.exists():
                    rel = str(md_file.relative_to(book_path))
                    issues.append(
                        f"断链：{rel} → 实体概念/{target}（概念卡片不存在）"
                    )
    
    return issues


def main():
    workspace = os.environ.get("CLAUDE_WORKSPACE")
    if not workspace:
        workspace = os.getcwd()
    
    total_issues = 0
    for entry in sorted(os.listdir(workspace)):
        book_path = os.path.join(workspace, entry)
        if not os.path.isdir(book_path) or entry.startswith("."):
            continue
        if not os.path.exists(os.path.join(book_path, "_目录.md")):
            continue
        
        issues = check_book(book_path)
        if issues:
            print(f"\n《{entry}》")
            for issue in issues:
                print(f"  - {issue}")
            total_issues += len(issues)
    
    if total_issues == 0:
        print("双向链接一致性检查通过")
    else:
        print(f"\n共发现 {total_issues} 个问题")


if __name__ == "__main__":
    main()
```

## 五、同步时机总结

| 触发方式 | 时机 | 做什么 | 实现层 |
|---------|------|-------|:---:|
| 自动 | 每次做阅读笔记后 | 更新小节 status + CLAUDE.md SYNC 块 | AI（SKILL 1.6） |
| 自动 | 每次创建/删除概念卡片后 | 更新 CLAUDE.md 实体概念数 | AI（SKILL 1.6） |
| 自动 | 每次对话结束 | 扫描文件系统，更新 CLAUDE.md 数字字段 | 脚本（Stop hook） |
| 主动 | `/sync-workspace` 或"同步工作区" | 完整对比 + 双向链接检查，输出报告 | AI（sync-workspace skill） |
| 主动 | "更新延伸方向 XXX" | 扫描笔记→概念的双向链接一致性 | AI（SKILL 2.4） |

## 六、与旧版方案对比

| 项目 | 旧版 | 改进版 |
|------|------|--------|
| 文件数 | 11 个 | 7 个 |
| commands | 5 个独立文件 | 0（合并到 skills，thin-wrapper 消除） |
| agents | 1 个 sync-checker | 0（逻辑已在 skill + hook 覆盖） |
| CLAUDE.md 同步 | 自然语言正则替换 | SYNC 不可见标记精确匹配 |
| auto-sync.py | sync_claude_md 空函数 | 完整实现：SYNC 块定位 + 数字更新 |
| 插件结构 | commands + agents 冗余 | skills + hooks 精简 |
| sync-workspace | command | 独立 skill（含完整同步报告格式） |

## 七、关键设计决策

1. **两层同步互补**：脚本层做确定性的数字更新（快、不消耗 token），AI 层做语义描述和交叉验证（需要理解力）。两层互不依赖。
2. **SYNC 标记**：CLAUDE.md 用 HTML 注释标记包围同步块，脚本可精确匹配替换，即使 CLAUDE.md 有其他内容也不影响。
3. **Stop hook 只碰数字**：阅读进度统计和实体概念数是可计算字段，自动更新。阅读状态、说明等语义字段只留给 AI 维护。
4. **commands 瘦身**：原方案中 init-book/read-section/create-concept 等 command 只是"指向 SKILL.md 某章节"的 thin wrapper，已由 SKILL.md 的触发描述覆盖。仅保留 sync-workspace 作为新功能独立 skill。
5. **check-consistency.py** 独立于 auto-sync.py，可被 Stop hook 调用（静默检查），也可被 sync-workspace skill 手动调用。

## 八、实现顺序

1. **SKILL.md 增量修改**：修改 CLAUDE.md 书籍条目模板（增加 SYNC 标记和阅读状态字段）+ 新增 1.6 节
2. **创建 sync-workspace skill**：`skills/sync-workspace/SKILL.md`
3. **创建 hooks 和脚本**：hooks.json、auto-sync.py、check-consistency.py
4. **创建 plugin.json**
5. **端到端测试**：用实际书籍测试完整流程
