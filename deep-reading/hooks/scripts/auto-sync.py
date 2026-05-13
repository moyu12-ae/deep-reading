#!/usr/bin/env python3
"""
自动同步脚本（Stop hook 触发）。
扫描工作区每本书的阅读进度和概念数量，更新 CLAUDE.md 中的 SYNC 块。
只做文件计数和精确文本替换，不做 AI 语义判断。
"""
import os
import re
from pathlib import Path


def parse_frontmatter_status(text):
    """从 YAML frontmatter 中提取 status 字段（纯标准库，不依赖 pyyaml）"""
    match = re.search(r'^status\s*:\s*(\S+)', text, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return "unread"


def count_statuses(book_path):
    """统计一本书中所有小节的 status 分布"""
    counts = {"unread": 0, "reading": 0, "completed": 0}
    for md_file in Path(book_path).rglob("*.md"):
        # 跳过实体概念文件夹（精确匹配目录名）、_开头的导航文件
        if md_file.parent.name == "实体概念" or md_file.name.startswith("_"):
            continue
        try:
            content = md_file.read_text()
            if content.startswith("---"):
                fm_end = content.find("---", 3)
                if fm_end > 0:
                    fm_text = content[3:fm_end]
                    status = parse_frontmatter_status(fm_text)
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
    start_marker = f"<!-- SYNC:BOOK:{book_name} -->"
    end_marker = "<!-- SYNC:END -->"

    start_pos = claude_content.find(start_marker)
    if start_pos == -1:
        return claude_content

    end_pos = claude_content.find(end_marker, start_pos)
    if end_pos == -1:
        return claude_content

    block = claude_content[start_pos:end_pos]

    # 替换阅读进度行
    block = re.sub(
        r'(- \*\*阅读进度\*\*[：:]\s*).*',
        lambda m: m.group(1) + progress_str,
        block
    )
    # 替换实体概念数行
    block = re.sub(
        r'(- \*\*实体概念数\*\*[：:]\s*)\d+',
        lambda m: m.group(1) + str(concept_count),
        block
    )

    return claude_content[:start_pos] + block + claude_content[end_pos:]


def main():
    workspace = os.environ.get("CLAUDE_PROJECT_DIR") or os.environ.get("CLAUDE_WORKSPACE")
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
        concept_count = count_concepts(book_path)

        if total > 0:
            progress_str = f"{total}个小节中 {counts['completed']}个已完成，{counts['reading']}个进行中，{counts['unread']}个未读"
        else:
            progress_str = f"0个小节中 0个已完成，0个进行中，0个未读"

        updated_content = update_sync_block(
            updated_content, book_name, progress_str, concept_count
        )

    if updated_content != content:
        with open(claude_path, "w") as f:
            f.write(updated_content)
        print(f"[auto-sync] CLAUDE.md updated")


if __name__ == "__main__":
    main()
