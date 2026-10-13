"""Validate only the explicitly approved distribution files using the standard library."""
from pathlib import Path
import ast
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
SKILL = "skills/lida-avatar-workflow/SKILL.md"
IGNORED_PARTS = {".git", "dist", "__pycache__"}
TEXT_EXTENSIONS = {".md", ".py", ".yml", ".yaml", ".json", ".svg", ".txt"}
ALLOWED_EXTENSIONS = TEXT_EXTENSIONS | {".png", ".jpg", ".jpeg", ""}
LOCAL_PATH = re.compile(r"(?i)(?:(?<![a-z0-9])[a-z]:[\\/]|" + r"file:" + r"//|/(?:Users|home)/)")
SECRET = re.compile(r"(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{30,}|-----BEGIN [A-Z ]*PRIVATE KEY-----)")
# Excluded names are stored as code points so they do not appear in distributed prose.
EXCLUDED_NAMES = ["".join(map(chr, values)) for values in (
    (86, 82, 111, 105, 100), (78, 84, 69), (12502, 12452, 12525, 12452, 12489),
)]


def slug(line):
    value = re.sub(r"^#{1,6}\s+", "", line).strip().lower()
    value = re.sub(r"[^\w\-\s]", "", value)
    return re.sub(r"\s+", "-", value)


def check_content(relative, text):
    problems = []
    if LOCAL_PATH.search(text):
        problems.append(f"{relative}: personal/local absolute path")
    if SECRET.search(text):
        problems.append(f"{relative}: credential-like content")
    if any(re.search(r"(?<![A-Za-z0-9])"+re.escape(name)+r"(?![A-Za-z0-9])", text, re.I)
           if name.isascii() else name in text for name in EXCLUDED_NAMES):
        problems.append(f"{relative}: excluded model name")
    return problems


def validate(root=ROOT):
    root = Path(root).resolve()
    errors = []
    try:
        manifest = json.loads((root / "publication-manifest.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return dict(passed=False, files=0, links=0, errors=["Publication manifest missing or invalid"])
    files = manifest.get("files", [])
    if not files or len(files) != len(set(files)):
        errors.append("Publication file list is empty or duplicated")
    expected = set(files)
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if any(part in IGNORED_PARTS for part in relative.parts) or not path.is_file():
            continue
        if relative.as_posix() not in expected:
            errors.append(f"{relative.as_posix()}: unlisted file")
    links = 0
    for relative in files:
        path = root / relative
        if not path.resolve().is_relative_to(root) or path.is_symlink():
            errors.append(f"{relative}: path leaves repository or is a symlink")
            continue
        if not path.is_file():
            errors.append(f"{relative}: missing")
            continue
        if path.suffix.lower() not in ALLOWED_EXTENSIONS or path.stat().st_size > 5 * 1024 * 1024:
            errors.append(f"{relative}: unsupported file type or size")
            continue
        if path.suffix.lower() in TEXT_EXTENSIONS or path.name in {"VERSION", ".gitignore", ".gitattributes"}:
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeError:
                errors.append(f"{relative}: UTF-8 required")
                continue
            errors.extend(check_content(relative, text))
            if path.suffix == ".py":
                try:
                    ast.parse(text)
                except SyntaxError:
                    errors.append(f"{relative}: Python syntax error")
            if path.suffix == ".md":
                for target in re.findall(r"!?\[[^\]]*\]\(([^\n]+?)\)", text):
                    target = target.strip().strip("<>")
                    if urlsplit(target).scheme in {"http", "https"}:
                        continue
                    links += 1
                    location, _, anchor = target.partition("#")
                    resolved = (path.parent / unquote(location)).resolve() if location else path
                    if not resolved.is_relative_to(root) or not resolved.is_file():
                        errors.append(f"{relative}: broken/outside local link")
                    elif resolved.relative_to(root).as_posix() not in expected:
                        errors.append(f"{relative}: linked file is not in package")
                    elif anchor and resolved.suffix == ".md":
                        headings = {slug(line) for line in resolved.read_text(encoding="utf-8").splitlines() if re.match(r"^#{1,6}\s", line)}
                        if unquote(anchor) not in headings:
                            errors.append(f"{relative}: missing section anchor")
            if path.suffix == ".svg":
                try:
                    svg = ET.fromstring(text)
                    for element in svg.iter():
                        if element.tag.split("}")[-1] in {"script", "foreignObject"}:
                            errors.append(f"{relative}: active SVG content")
                        for key, value in element.attrib.items():
                            if key.lower().startswith("on") or (key.split("}")[-1] == "href" and not value.startswith("#")):
                                errors.append(f"{relative}: external/active SVG reference")
                except ET.ParseError:
                    errors.append(f"{relative}: invalid SVG")
    for relative, expected_hash in manifest.get("asset_sha256", {}).items():
        path = root / relative
        if relative not in expected or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected_hash:
            errors.append(f"{relative}: image hash mismatch/unlisted")
    if SKILL in expected and (root / SKILL).is_file():
        text = (root / SKILL).read_text(encoding="utf-8")
        if not re.match(r"\A---\nname: lida-avatar-workflow\ndescription: .+\n---\n", text):
            errors.append("Skill frontmatter/name/description invalid")
        if re.search(r"\b(?:TODO|TBD)\b", text):
            errors.append("Skill contains scaffold placeholders")
    version = (root / "VERSION").read_text(encoding="utf-8").strip() if (root / "VERSION").is_file() else ""
    if not re.fullmatch(r"\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?", version):
        errors.append("VERSION must contain a valid development/release version")
    return dict(passed=not errors, files=len(files), links=links, errors=errors)


if __name__ == "__main__":
    result = validate()
    print(json.dumps(result, ensure_ascii=False))
    sys.exit(0 if result["passed"] else 1)
