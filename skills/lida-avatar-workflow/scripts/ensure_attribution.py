"""Explicit attribution helper for publishing apps or skills incorporating these materials.

Reading this skill to make a model does not require output credits. Importing this
module does not inspect or modify projects. Only an explicitly supplied existing
project directory can receive THIRD_PARTY_NOTICES.md.
"""
from pathlib import Path
import argparse
import json
import re

SOURCES = {
    "skills": ("3DCharaMakeSkills-Lida", "https://github.com/Lida-V/3DCharaMakeSkills-Lida"),
    "shader": ("LidaAngelToon", "https://github.com/Lida-V/LidaAngelToon"),
}
DEFAULT_CHANGES = "制作手順・実装の参考として利用。具体的な利用・改変箇所は配布者が記載。"
NOTICE_NAME = "THIRD_PARTY_NOTICES.md"


def markers(component):
    return (f"<!-- lida-attribution:{component}:start -->",
            f"<!-- lida-attribution:{component}:end -->")


def valid_section(text, component):
    name, url = SOURCES[component]
    author = re.search(r"(?mi)^\s*(?:[-*]\s*)?(?:作者|著者|Author)\s*[:：]\s*Lida\b", text)
    changes = re.search(r"(?mi)^\s*(?:[-*]\s*)?(?:変更(?:内容|注記|箇所)?|Modifications?|Changes?)\s*[:：]\s*\S", text)
    return name in text and url in text and bool(author) and bool(changes)


def has_attribution(text, component):
    start, end = markers(component)
    if start in text or end in text:
        if text.count(start) != 1 or text.count(end) != 1:
            raise ValueError(f"{component}: attribution markers must form one complete block")
        begin, finish = text.index(start), text.index(end)
        if finish < begin or not valid_section(text[begin:finish], component):
            raise ValueError(f"{component}: existing attribution is incomplete; preserve and repair it manually")
        return True
    # Respect a complete manually maintained entry instead of appending a duplicate.
    sections = re.split(r"(?m)(?=^#{1,6}\s+)", text)
    return any(valid_section(section, component) for section in sections)


def attribution_block(component, changes):
    name, url = SOURCES[component]
    start, end = markers(component)
    return (f"{start}\n## 参照元: {name}\n\n"
            f"- 出典: {name}\n- 作者: Lida\n- URL: {url}\n"
            f"- 変更注記: {changes}\n"
            "- 利用条件: 元資料のLICENSEとNOTICE.mdを参照。資料そのものを再配布する場合は両方を保持してください。\n"
            f"{end}\n")


def ensure_attribution(project_dir=None, target=None, component=None, changes=None, check=False):
    if target == "model":
        return dict(passed=True, required=False, changed=False,
                    reason="モデル制作の成果物へのクレジットは不要です。")
    if target not in {"app", "skill"}:
        raise ValueError("Explicit target app, skill, or model is required")
    if component not in {"skills", "shader", "both"}:
        raise ValueError("Publishing an app/skill requires explicit component skills, shader, or both")
    if project_dir is None:
        raise ValueError("Publishing an app/skill requires an explicit existing project directory")
    project = Path(project_dir).expanduser().resolve()
    if not project.is_dir():
        raise ValueError("The explicitly supplied project directory must already exist")
    portable = Path(__file__).resolve().parents[1]
    for name in ("LICENSE", "NOTICE.md"):
        source = portable / name
        if not source.is_file() or not source.read_text(encoding="utf-8").strip():
            raise ValueError(f"Portable skill is incomplete: {name} is missing or empty")
    output = project / NOTICE_NAME
    if output.is_symlink() or (output.exists() and not output.is_file()):
        raise ValueError("Refusing a symlink or non-file attribution destination")
    before = output.read_bytes() if output.exists() else b""
    text = before.decode("utf-8-sig")
    components = ["skills", "shader"] if component == "both" else [component]
    missing = [item for item in components if not has_attribution(text, item)]
    if check or not missing:
        return dict(passed=not missing, required=True, changed=False, missing=missing,
                    file=NOTICE_NAME, target=target, components=components)
    note = DEFAULT_CHANGES if changes is None else changes.strip()
    if not note or "<!-- lida-attribution:" in note:
        raise ValueError("Changes must be nonempty plain attribution notes without helper markers")
    additions = "\n\n".join(attribution_block(item, note).rstrip() for item in missing) + "\n"
    if not before:
        addition_bytes = ("# Third-party notices\n\n" + additions).encode("utf-8")
        with output.open("xb") as handle:
            handle.write(addition_bytes)
    else:
        # Preserve every existing byte, including custom changes notes and line endings.
        separator = b"" if before.endswith(b"\n\n") else b"\n" if before.endswith(b"\n") else b"\n\n"
        with output.open("ab") as handle:
            handle.write(separator + additions.encode("utf-8"))
    return dict(passed=True, required=True, changed=True, added=missing,
                file=NOTICE_NAME, target=target, components=components)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", required=True, choices=("model", "app", "skill"))
    parser.add_argument("--component", choices=("skills", "shader", "both"))
    parser.add_argument("--project-dir", type=Path, help="Explicit existing publishing project directory")
    parser.add_argument("--changes", help="Actual usage/modifications; existing entries are preserved")
    parser.add_argument("--check", action="store_true", help="Check required source entries without writing")
    args = parser.parse_args(argv)
    try:
        result = ensure_attribution(args.project_dir, args.target, args.component, args.changes, args.check)
    except (OSError, UnicodeError, ValueError) as exc:
        print(json.dumps(dict(passed=False, error=str(exc)), ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
