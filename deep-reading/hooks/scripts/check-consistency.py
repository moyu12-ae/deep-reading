#!/usr/bin/env python3
"""
双向链接一致性检查。
检查概念卡片的 source 指向的笔记文件是否存在，
以及笔记中"本节概念"的 wikilink 目标概念卡片是否存在。
"""
import os
import re
from pathlib import Path


def extract_wikilinks(text):
    """提取所有 [[目标|别名]] 或 [[目标]] 中的目标文件名"""
    links = re.findall(r'\[\[(.*?)(?:\|.*?)?\]\]', text)
    targets = []
    for link in links:
        name = link.strip().split("/")[-1]
        targets.append(name)
    return targets


def parse_frontmatter_field(text, field):
    """从 YAML frontmatter 中提取指定字段值（纯标准库，不依赖 pyyaml）"""
    match = re.search(rf'^{field}\s*:\s*(.+)', text, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return ""


def parse_frontmatter_list(text, field):
    """从 YAML frontmatter 中提取列表字段"""
    values = []
    lines = text.split("\n")
    in_field = False
    for line in lines:
        if in_field:
            match = re.match(r'\s+-\s*(.+)', line)
            if match:
                values.append(match.group(1).strip())
            elif re.match(r'^\w', line):
                break
        if re.match(rf'^{field}\s*:', line):
            in_field = True
            # 内联列表: field: ["a", "b"]
            inline = re.findall(r'"([^"]+)"', line)
            if inline:
                values = inline
                break
    return values


def parse_frontmatter(content):
    """解析 YAML frontmatter，返回简易字典"""
    if not content.startswith("---"):
        return {}
    fm_end = content.find("---", 3)
    if fm_end > 0:
        fm_text = content[3:fm_end]
        return {
            "status": parse_frontmatter_field(fm_text, "status"),
            "source": parse_frontmatter_list(fm_text, "source"),
        }
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
        if md_file.parent.name == "实体概念" or md_file.name.startswith("_"):
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
        if md_file.parent.name == "实体概念" or md_file.name.startswith("_"):
            continue
        content = md_file.read_text()
        fm = parse_frontmatter(content)

        if fm.get("status") == "unread":
            continue

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
    workspace = os.environ.get("CLAUDE_PROJECT_DIR") or os.environ.get("CLAUDE_WORKSPACE")
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
        print(f"\n共发现 {total_issues} 个断链")


if __name__ == "__main__":
    main()
