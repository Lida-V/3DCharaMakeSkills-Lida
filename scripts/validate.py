"""Validate the publication allowlist, portable notices, and approved file contents."""
from pathlib import Path, PurePosixPath
import ast
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = "skills/lida-avatar-workflow"
SKILL = SKILL_DIR + "/SKILL.md"
ATTRIBUTION_HELPER = SKILL_DIR + "/scripts/ensure_attribution.py"
REQUIRED_FILES = {"LICENSE", "NOTICE.md", SKILL, ATTRIBUTION_HELPER,
                  SKILL_DIR + "/LICENSE", SKILL_DIR + "/NOTICE.md",
                  "VERSION", "publication-manifest.json"}
IGNORED_PARTS = {".git", "dist", "__pycache__"}
TEXT_EXTENSIONS = {".md", ".py", ".yml", ".yaml", ".json", ".svg", ".txt", ""}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".svg"}
ALLOWED_EXTENSIONS = TEXT_EXTENSIONS | IMAGE_EXTENSIONS
LOCAL_PATH = re.compile(r"(?i)(?:(?<![a-z0-9])[a-z]:[\\/]|" + r"file:" + r"//|/(?:Users|home)/)")
SECRET = re.compile(r"(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{30,}|-----BEGIN [A-Z ]*PRIVATE KEY-----)")
# Keep excluded names out of distributed prose.
EXCLUDED_NAMES = ["".join(map(chr, values)) for values in (
    (86, 82, 111, 105, 100), (78, 84, 69), (12502, 12452, 12525, 12489),
)]


def slug(line):
    value = re.sub(r"^#{1,6}\s+", "", line).strip().lower()
    value = re.sub(r"[^\w\-\s]", "", value)
    return re.sub(r"\s+", "-", value)


def safe_relative(relative):
    if not isinstance(relative, str) or not relative or "\\" in relative or ":" in relative or "\x00" in relative:
        return False
    path = PurePosixPath(relative)
    return (not path.is_absolute() and path.as_posix() == relative
            and all(part not in {"", ".", ".."} for part in relative.split("/"))
            and not any(part in IGNORED_PARTS for part in path.parts))


def is_fbx(data):
    """Recognize binary and ASCII FBX even when the extension was changed."""
    head = data[:8192].lstrip(b"\xef\xbb\xbf \t\r\n")
    return (head.startswith(b"Kaydara FBX Binary")
            or re.match(rb";\s*FBX\s+\d+(?:\.\d+).*project file", head, re.I) is not None
            or re.match(rb"FBXHeaderExtension\s*:", head) is not None)


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


def check_file_bytes(relative, data):
    """Content checks shared by source and completed ZIP validation."""
    problems = []
    suffix = PurePosixPath(relative).suffix.lower()
    if suffix == ".fbx" or is_fbx(data):
        return [f"{relative}: reference motion/FBX must not be distributed"]
    if suffix not in ALLOWED_EXTENSIONS or len(data) > 5 * 1024 * 1024:
        return [f"{relative}: unsupported file type or size"]
    if suffix == ".png" and not (len(data) >= 24 and data.startswith(b"\x89PNG\r\n\x1a\n") and data[12:16] == b"IHDR"):
        problems.append(f"{relative}: invalid PNG signature")
    if suffix in {".jpg", ".jpeg"} and not (data.startswith(b"\xff\xd8\xff") and data.endswith(b"\xff\xd9")):
        problems.append(f"{relative}: invalid JPEG signature")
    if suffix in TEXT_EXTENSIONS or PurePosixPath(relative).name in {".gitignore", ".gitattributes"}:
        try:
            text = data.decode("utf-8")
        except UnicodeError:
            return problems + [f"{relative}: UTF-8 required"]
        problems.extend(check_content(relative, text))
        if suffix == ".py":
            try:
                ast.parse(text)
            except SyntaxError:
                problems.append(f"{relative}: Python syntax error")
        if suffix == ".svg":
            try:
                svg = ET.fromstring(text)
                if svg.tag.split("}")[-1] != "svg":
                    problems.append(f"{relative}: SVG root required")
                for element in svg.iter():
                    if element.tag.split("}")[-1] in {"script", "foreignObject"}:
                        problems.append(f"{relative}: active SVG content")
                    for key, value in element.attrib.items():
                        if key.lower().startswith("on") or (key.split("}")[-1] == "href" and not value.startswith("#")):
                            problems.append(f"{relative}: external/active SVG reference")
            except ET.ParseError:
                problems.append(f"{relative}: invalid SVG")
    return problems


def check_translations(manifest, contents):
    """Check coverage and reviewed source versions, not translation meaning."""
    support = manifest.get("language_support")
    if support is None:
        return ["Language support declaration is required"]
    errors = []
    if (not isinstance(support, dict) or support.get("primary") != "ja"
            or support.get("available") != ["ja", "en"] or not isinstance(support.get("pairs"), list)):
        return ["Language support must declare ja/en and translation pairs"]
    sources = set()
    translations = set()
    translated = {}
    for pair in support["pairs"]:
        if not isinstance(pair, dict) or set(pair) != {"source", "translation", "source_sha256"}:
            errors.append("Translation pair fields are invalid")
            continue
        source, target = pair["source"], pair["translation"]
        if not safe_relative(source) or not safe_relative(target) or source == target:
            errors.append("Translation paths must be distinct canonical files")
            continue
        if source.casefold() in sources or target.casefold() in translations:
            errors.append("Translation pair is duplicated")
        sources.add(source.casefold())
        translations.add(target.casefold())
        translated[source] = target
        if source not in contents or target not in contents:
            errors.append(f"{source}: source or English translation is missing from package")
        else:
            try:
                translation_text = contents[target].decode("utf-8-sig")
            except UnicodeError:
                errors.append(f"{target}: English translation must be UTF-8")
            else:
                if not translation_text.strip():
                    errors.append(f"{target}: English translation is empty")
            if hashlib.sha256(contents[source]).hexdigest() != pair["source_sha256"]:
                errors.append(f"{source}: English translation source version is stale; review before updating its hash")
    required = {"README.md": "README.en.md", SKILL: SKILL_DIR + "/SKILL.en.md"}
    prefix = SKILL_DIR + "/references/"
    for source in contents:
        if source.startswith(prefix) and source.endswith(".md") and "/" not in source[len(prefix):]:
            required[source] = prefix + "en/" + source[len(prefix):]
    for source, target in required.items():
        if translated.get(source) != target:
            errors.append(f"{source}: corresponding English document is not registered")
    return errors


def validate(root=ROOT):
    root = Path(root).resolve()
    errors = []
    try:
        manifest = json.loads((root / "publication-manifest.json").read_text(encoding="utf-8"))
        if not isinstance(manifest, dict):
            raise ValueError("object required")
    except (OSError, ValueError, UnicodeError):
        return dict(passed=False, files=0, links=0, errors=["Publication manifest missing or invalid"])
    files = manifest.get("files", [])
    if not isinstance(files, list) or not all(safe_relative(item) for item in files):
        return dict(passed=False, files=0, links=0, errors=["Publication paths must be canonical relative file paths"])
    if not files or len(files) != len({item.casefold() for item in files}):
        errors.append("Publication file list is empty or duplicated")
    expected = set(files)
    for required in sorted(REQUIRED_FILES - expected):
        errors.append(f"{required}: mandatory distribution file not listed")
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if any(part in IGNORED_PARTS for part in relative.parts) or not path.is_file():
            continue
        if relative.as_posix() not in expected:
            errors.append(f"{relative.as_posix()}: unlisted file")
    links = 0
    contents = {}
    for relative in files:
        path = root / relative
        if (not path.resolve().is_relative_to(root)
                or any(parent.is_symlink() for parent in [path, *path.parents] if parent.is_relative_to(root))):
            errors.append(f"{relative}: path leaves repository or is a symlink")
            continue
        if not path.is_file():
            errors.append(f"{relative}: missing")
            continue
        data = path.read_bytes()
        contents[relative] = data
        errors.extend(check_file_bytes(relative, data))
        if path.suffix.lower() == ".md":
            try:
                text = data.decode("utf-8")
            except UnicodeError:
                continue
            for target in re.findall(r"!?\[[^\]]*\]\(([^\n]+?)\)", text):
                target = target.strip().strip("<>")
                if urlsplit(target).scheme in {"http", "https"}:
                    continue
                links += 1
                location, _, anchor = target.partition("#")
                resolved = (path.parent / unquote(location)).resolve() if location else path
                if not resolved.is_relative_to(root) or not resolved.is_file():
                    errors.append(f"{relative}: broken/outside local link")
                elif relative.startswith(SKILL_DIR + "/") and not resolved.is_relative_to(root / SKILL_DIR):
                    errors.append(f"{relative}: local link leaves portable skill folder")
                elif resolved.relative_to(root).as_posix() not in expected:
                    errors.append(f"{relative}: linked file is not in package")
                elif anchor and resolved.suffix == ".md":
                    try:
                        headings = {slug(line) for line in resolved.read_text(encoding="utf-8").splitlines() if re.match(r"^#{1,6}\s", line)}
                        if unquote(anchor) not in headings:
                            errors.append(f"{relative}: missing section anchor")
                    except UnicodeError:
                        errors.append(f"{relative}: linked document is not UTF-8")
    errors.extend(check_translations(manifest, contents))
    assets = manifest.get("asset_sha256", {})
    if not isinstance(assets, dict):
        errors.append("asset_sha256 must be a mapping")
        assets = {}
    image_files = {name for name in files if PurePosixPath(name).suffix.lower() in IMAGE_EXTENSIONS}
    for relative in sorted(image_files - set(assets)):
        errors.append(f"{relative}: approved image hash required")
    for relative, expected_hash in assets.items():
        if (relative not in image_files or relative not in contents
                or hashlib.sha256(contents[relative]).hexdigest() != expected_hash):
            errors.append(f"{relative}: image hash mismatch/unlisted")
    for relative in ("LICENSE", "NOTICE.md", "LICENSE.en.md", "NOTICE.en.md"):
        portable = SKILL_DIR + "/" + relative
        if relative in contents and portable in contents:
            try:
                primary = contents[relative].decode("utf-8").replace("\r\n", "\n")
                copied = contents[portable].decode("utf-8").replace("\r\n", "\n")
                if not primary.strip() or primary != copied:
                    errors.append(f"{portable}: must match nonempty root {relative}")
            except UnicodeError:
                errors.append(f"{portable}: license/notice must be UTF-8")
    if SKILL in contents:
        text = contents[SKILL].decode("utf-8", errors="replace").replace("\r\n", "\n")
        if not re.match(r"\A---\nname: lida-avatar-workflow\ndescription: .+\n---\n", text):
            errors.append("Skill frontmatter/name/description invalid")
        if re.search(r"\b(?:TODO|TBD)\b", text):
            errors.append("Skill contains scaffold placeholders")
    version = contents.get("VERSION", b"").decode("utf-8", errors="replace").strip()
    if not re.fullmatch(r"\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?", version):
        errors.append("VERSION must contain a valid development/release version")
    if manifest.get("version") != version:
        errors.append("Manifest version must match VERSION")
    return dict(passed=not errors, files=len(files), links=links, errors=errors)


if __name__ == "__main__":
    result = validate()
    print(json.dumps(result, ensure_ascii=False))
    sys.exit(0 if result["passed"] else 1)
