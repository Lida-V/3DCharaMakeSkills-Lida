# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Lida
"""Read an exported VRM (glb) and list settings that silently went wrong. Ordinary Python; no Blender, no numpy.

check: --input MODEL.vrm --report NEW.json [--max-texture 2048] [--expect-mtoon all|any|ignore]
       [--expect-expressions aa ih ...] [--allow-extension NAME ...]

An exporter can report success while materials fell back to PBR, spring gravity points sideways, hit
radii are zero, collider groups are empty, or the look-at origin uses the wrong axis. This command
reads only the JSON chunk and image headers of the file and checks: container, VRM version, required
humanoid bones, materials (MToon or not), spring bones (gravity direction, hit radius, collider
references), look-at offset, expressions and their morph binds, meshes (UV0, weights, triangles),
images (format, size) and required extensions. It never modifies the input. The report must be a new
path. Exit codes: 0 no findings; 2 warnings or errors found in the file; 1 invalid input or I/O error.
Passing this check does not grade appearance or behaviour in a viewer or engine.
"""

import argparse
import base64
import hashlib
import json
import math
from pathlib import Path
import struct
import sys


REPORT_SCHEMA = "lida.vrm-check.report.v1"
REQUIRED_BONES = ("hips", "spine", "head", "leftUpperArm", "leftLowerArm", "leftHand", "rightUpperArm", "rightLowerArm",
                  "rightHand", "leftUpperLeg", "leftLowerLeg", "leftFoot", "rightUpperLeg", "rightLowerLeg", "rightFoot")
EXPECTED_EXPRESSIONS = ("aa", "ih", "ou", "ee", "oh", "blink", "blinkLeft", "blinkRight", "happy", "angry", "sad", "relaxed", "surprised")
KNOWN_EXTENSIONS = {"VRMC_vrm", "VRMC_springBone", "VRMC_materials_mtoon", "VRMC_node_constraint", "VRMC_materials_hdr_emissiveMultiplier",
                    "VRMC_vrm_animation", "VRM", "KHR_materials_unlit", "KHR_texture_transform", "KHR_materials_emissive_strength"}
UNVERIFIED = [
    "appearance and motion in the destination viewer or engine (shading, outline, sway, expressions)",
    "mesh shapes, weights and morph data themselves (only their presence and index ranges are read)",
    "whether collider sizes and positions suit the body, and whether springs behave in motion",
    "licence and metadata wording beyond presence",
]


def read_glb(data):
    """Return (json dict, binary chunk or b'')."""
    if len(data) < 20 or data[:4] != b"glTF":
        raise ValueError("Not a binary glTF/VRM file")
    version, total = struct.unpack_from("<II", data, 4)
    if version != 2:
        raise ValueError("Unsupported glTF container version: %d" % version)
    if total > len(data):
        raise ValueError("The file is shorter than its header says")
    offset, document, binary = 12, None, b""
    while offset + 8 <= total:
        length, kind = struct.unpack_from("<I4s", data, offset)
        chunk = data[offset + 8: offset + 8 + length]
        if kind == b"JSON" and document is None:
            document = json.loads(chunk.decode("utf-8"))
        elif kind == b"BIN\x00" and not binary:
            binary = chunk
        offset += 8 + length + (-length % 4)
    if document is None:
        raise ValueError("No JSON chunk in the file")
    return document, binary


def image_size(blob):
    """(format, width, height) from a PNG or JPEG header; (name, None, None) otherwise."""
    if blob[:8] == b"\x89PNG\r\n\x1a\n" and len(blob) >= 24:
        return ("png",) + struct.unpack(">II", blob[16:24])
    if blob[:2] == b"\xff\xd8":
        offset = 2
        while offset + 9 < len(blob):
            if blob[offset] != 0xFF:
                offset += 1
                continue
            marker = blob[offset + 1]
            if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                height, width = struct.unpack(">HH", blob[offset + 5: offset + 9])
                return "jpeg", width, height
            if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
                offset += 2
                continue
            offset += 2 + struct.unpack(">H", blob[offset + 2: offset + 4])[0]
        return "jpeg", None, None
    if blob[:12] == b"\xabKTX 20\xbb\r\n\x1a\n":
        return "ktx2", None, None
    if blob[:4] == b"RIFF" and blob[8:12] == b"WEBP":
        return "webp", None, None
    return "unknown", None, None


class _Findings:
    def __init__(self):
        self.items = []

    def add(self, level, code, message, **detail):
        entry = {"level": level, "code": code, "message": message}
        entry.update(detail)
        self.items.append(entry)


def _down_share(direction):
    length = math.sqrt(sum(float(v) ** 2 for v in direction))
    return -float(direction[1]) / length if length > 0 else 0.0


def _check_images(document, binary, limit, found):
    views = document.get("bufferViews", [])
    rows, largest, total = [], 0, 0
    for index, image in enumerate(document.get("images", [])):
        blob, where = b"", "bufferView"
        if "bufferView" in image and image["bufferView"] < len(views):
            view = views[image["bufferView"]]
            start = view.get("byteOffset", 0)
            blob = binary[start: start + view.get("byteLength", 0)]
        elif str(image.get("uri", "")).startswith("data:"):
            where = "data uri"
            blob = base64.b64decode(image["uri"].split(",", 1)[1])
        else:
            where = "external file"
            found.add("warning", "image_external", "Image %d (%s) is an external file; a single-file VRM cannot carry it" % (index, image.get("name", "")))
        kind, width, height = image_size(blob) if blob else ("unknown", None, None)
        total += len(blob)
        row = {"index": index, "name": image.get("name", ""), "format": kind, "width": width, "height": height, "bytes": len(blob), "stored": where}
        rows.append(row)
        if blob and kind not in ("png", "jpeg"):
            found.add("warning", "image_format", "Image %d (%s) is %s; many VRM loaders read only PNG and JPEG" % (index, row["name"], kind))
        if width and height:
            largest = max(largest, width, height)
            if max(width, height) > limit:
                found.add("warning", "image_large", "Image %d (%s) is %dx%d, larger than %d" % (index, row["name"], width, height, limit))
    return {"count": len(rows), "largest_side": largest, "bytes": total, "over_limit": sum(1 for r in rows if r["width"] and max(r["width"], r["height"]) > limit)}, rows


def _check_meshes(document, found):
    accessors = document.get("accessors", [])
    triangles = primitives = targets = no_uv = 0
    target_counts = {}
    for index, mesh in enumerate(document.get("meshes", [])):
        counts = set()
        for primitive in mesh.get("primitives", []):
            primitives += 1
            attributes = primitive.get("attributes", {})
            if "TEXCOORD_0" not in attributes:
                no_uv += 1
            if ("JOINTS_0" in attributes) != ("WEIGHTS_0" in attributes):
                found.add("error", "skin_incomplete", "Mesh %d (%s) has joints without weights or weights without joints" % (index, mesh.get("name", "")))
            if primitive.get("mode", 4) == 4:
                source = primitive.get("indices", attributes.get("POSITION"))
                if isinstance(source, int) and source < len(accessors):
                    triangles += accessors[source].get("count", 0) // 3
            counts.add(len(primitive.get("targets", [])))
        if len(counts) > 1:
            found.add("error", "targets_differ", "Mesh %d (%s) has primitives with different numbers of morph targets" % (index, mesh.get("name", "")))
        target_counts[index] = min(counts) if counts else 0
        targets += target_counts[index]
    if no_uv:
        found.add("warning", "uv_missing", "%d primitives have no TEXCOORD_0; tangents are undefined and some exporters stop on them" % no_uv)
    return {"meshes": len(document.get("meshes", [])), "primitives": primitives, "triangles": triangles, "morph_targets": targets,
            "primitives_without_uv0": no_uv}, target_counts


def _check_humanoid(vrm, nodes, found):
    bones = (vrm.get("humanoid") or {}).get("humanBones") or {}
    missing = [name for name in REQUIRED_BONES if name not in bones]
    if missing:
        found.add("error", "humanoid_missing", "Required humanoid bones are missing: " + ", ".join(missing))
    used = {}
    for name, entry in bones.items():
        node = entry.get("node")
        if not isinstance(node, int) or not 0 <= node < nodes:
            found.add("error", "humanoid_node", "Humanoid bone %s points to a node that does not exist" % name)
        elif node in used:
            found.add("error", "humanoid_duplicate", "Humanoid bones %s and %s use the same node" % (used[node], name))
        else:
            used[node] = name
    return {"bones": len(bones), "missing_required": missing}


def _check_materials(document, expect, found):
    materials = document.get("materials", [])
    plain = [m.get("name", str(i)) for i, m in enumerate(materials) if "VRMC_materials_mtoon" not in (m.get("extensions") or {})]
    mtoon = len(materials) - len(plain)
    if expect == "all" and plain:
        found.add("warning", "mtoon_missing", "%d of %d materials are not MToon (exported as PBR or unlit): %s"
                  % (len(plain), len(materials), ", ".join(plain[:12]) + (" ..." if len(plain) > 12 else "")))
    if expect == "any" and materials and not mtoon:
        found.add("warning", "mtoon_none", "No material is MToon; the toon setup did not reach the file")
    outline = sum(1 for m in materials if ((m.get("extensions") or {}).get("VRMC_materials_mtoon") or {}).get("outlineWidthMode", "none") != "none")
    blend = sum(1 for m in materials if m.get("alphaMode") == "BLEND")
    zwrite = sum(1 for m in materials if ((m.get("extensions") or {}).get("VRMC_materials_mtoon") or {}).get("transparentWithZWrite"))
    if zwrite:
        found.add("warning", "blend_zwrite", "%d BLEND materials write depth; in some viewers transparent pixels hide what is behind them "
                  "(consider MASK for feathers and hair cards)" % zwrite)
    return {"count": len(materials), "mtoon": mtoon, "not_mtoon": plain, "with_outline": outline, "alpha_blend": blend, "blend_with_zwrite": zwrite}


def _check_springs(spring, nodes, found):
    colliders = spring.get("colliders", [])
    groups = spring.get("colliderGroups", [])
    springs = spring.get("springs", [])
    used_groups, used_colliders, joints, zero_hit, sideways, owners = set(), set(), 0, [], {}, {}
    for index, collider in enumerate(colliders):
        shape = collider.get("shape") or {}
        radius = (shape.get("sphere") or shape.get("capsule") or {}).get("radius", 0)
        if not radius or radius <= 0:
            found.add("warning", "collider_radius", "Collider %d has no radius" % index)
        if not isinstance(collider.get("node"), int) or not 0 <= collider["node"] < nodes:
            found.add("error", "collider_node", "Collider %d points to a node that does not exist" % index)
    for index, group in enumerate(groups):
        members = group.get("colliders", [])
        if not members:
            found.add("warning", "group_empty", "Collider group %d (%s) is empty" % (index, group.get("name", "")))
        for member in members:
            if not isinstance(member, int) or not 0 <= member < len(colliders):
                found.add("error", "group_collider", "Collider group %d (%s) refers to a collider that does not exist" % (index, group.get("name", "")))
            else:
                used_colliders.add(member)
    for index, item in enumerate(springs):
        name = item.get("name", str(index))
        chain = item.get("joints", [])
        joints += len(chain)
        if len(chain) < 2:
            found.add("warning", "spring_short", "Spring %s has fewer than two joints; the last joint is only an end mark and does not turn" % name)
        refs = item.get("colliderGroups", [])
        for ref in refs:
            if not isinstance(ref, int) or not 0 <= ref < len(groups):
                found.add("error", "spring_group", "Spring %s refers to a collider group that does not exist" % name)
            else:
                used_groups.add(ref)
        moving = chain[:-1] if len(chain) > 1 else chain
        if refs and moving and all(not j.get("hitRadius") for j in moving):
            zero_hit.append(name)
        for joint in moving:
            node = joint.get("node")
            if not isinstance(node, int) or not 0 <= node < nodes:
                found.add("error", "joint_node", "Spring %s has a joint on a node that does not exist" % name)
                continue
            if node in owners and owners[node] != name:
                found.add("warning", "joint_shared", "Node %d is a joint of springs %s and %s" % (node, owners[node], name))
            owners[node] = name
            direction = joint.get("gravityDir", [0, -1, 0])
            if joint.get("gravityPower", 0) > 0 and _down_share(direction) < 0.9:
                sideways.setdefault(tuple(round(float(v), 3) for v in direction), []).append(name)
    if zero_hit:
        found.add("warning", "hit_radius_zero", "%d springs use colliders but every joint has hit radius 0, so nothing can collide: %s"
                  % (len(zero_hit), ", ".join(zero_hit[:10]) + (" ..." if len(zero_hit) > 10 else "")))
    for direction, names in sideways.items():
        found.add("warning", "gravity_direction", "Gravity of %d joints points to %s, not down (0, -1, 0 in VRM's Y-up axes): %s"
                  % (len(names), list(direction), ", ".join(sorted(set(names))[:8])))
    idle = [i for i in range(len(groups)) if i not in used_groups]
    if idle:
        found.add("warning", "group_unused", "%d collider groups are not used by any spring: %s"
                  % (len(idle), ", ".join(str(groups[i].get("name", i)) for i in idle[:10])))
    return {"springs": len(springs), "joints": joints, "colliders": len(colliders), "collider_groups": len(groups),
            "springs_without_colliders": sum(1 for s in springs if not s.get("colliderGroups")),
            "unused_colliders": len(colliders) - len(used_colliders), "unused_groups": len(idle)}


def _check_expressions(vrm, document, target_counts, expected, found):
    block = vrm.get("expressions") or {}
    preset, custom = block.get("preset") or {}, block.get("custom") or {}
    missing = [name for name in expected if name not in preset]
    if missing:
        found.add("warning", "expression_missing", "Expected preset expressions are missing: " + ", ".join(missing))
    nodes = document.get("nodes", [])
    empty, overrides = [], {}
    for name, item in list(preset.items()) + list(custom.items()):
        binds = item.get("morphTargetBinds") or []
        if not binds and not item.get("materialColorBinds") and not item.get("textureTransformBinds"):
            empty.append(name)
        for bind in binds:
            node = bind.get("node")
            mesh = nodes[node].get("mesh") if isinstance(node, int) and 0 <= node < len(nodes) else None
            if mesh is None:
                found.add("error", "bind_node", "Expression %s binds a node without a mesh" % name)
            elif not 0 <= bind.get("index", -1) < target_counts.get(mesh, 0):
                found.add("error", "bind_index", "Expression %s binds morph target %s, but the mesh has %d" % (name, bind.get("index"), target_counts.get(mesh, 0)))
        rule = {k: item[k] for k in ("overrideBlink", "overrideLookAt", "overrideMouth") if item.get(k, "none") != "none"}
        if rule:
            overrides[name] = rule
    gaze_by_bone = (vrm.get("lookAt") or {}).get("type", "bone") != "expression"
    quiet = {"neutral"} | ({"lookUp", "lookDown", "lookLeft", "lookRight"} if gaze_by_bone else set())
    empty = [name for name in empty if name not in quiet]       # these are normally empty
    if empty:
        found.add("warning", "expression_empty", "Expressions without any bind: " + ", ".join(empty))
    return {"preset": sorted(preset), "custom": sorted(custom), "missing_expected": missing, "empty": empty, "overrides": overrides}


def _check_vrm0(legacy, document, expect, found):
    found.add("info", "vrm0", "This is a VRM 0.x file; only materials, spring gravity, hit radius and images are checked")
    shaders = [p.get("shader", "") for p in legacy.get("materialProperties", [])]
    plain = [p.get("name", "") for p in legacy.get("materialProperties", []) if "MToon" not in p.get("shader", "")]
    if expect == "all" and plain:
        found.add("warning", "mtoon_missing", "%d of %d materials are not MToon: %s" % (len(plain), len(shaders), ", ".join(plain[:12])))
    groups = (legacy.get("secondaryAnimation") or {}).get("boneGroups", [])
    for index, group in enumerate(groups):
        direction = group.get("gravityDir") or {}
        vector = [direction.get("x", 0), direction.get("y", -1), direction.get("z", 0)]
        if group.get("gravityPower", 0) > 0 and _down_share(vector) < 0.9:
            found.add("warning", "gravity_direction", "Gravity of bone group %d points to %s, not down" % (index, vector))
        if group.get("colliderGroups") and not group.get("hitRadius"):
            found.add("warning", "hit_radius_zero", "Bone group %d uses colliders but its hit radius is 0" % index)
    return {"materials": {"count": len(shaders), "mtoon": len(shaders) - len(plain), "not_mtoon": plain}, "springs": {"bone_groups": len(groups)}}


def check_document(document, binary=b"", options=None):
    """Check a parsed glTF/VRM document; returns the report body (no file access)."""
    opt = {"max_texture": 2048, "expect_mtoon": "all", "expect_expressions": list(EXPECTED_EXPRESSIONS), "allow_extensions": []}
    opt.update({k: v for k, v in (options or {}).items() if v is not None})
    if opt["expect_mtoon"] not in ("all", "any", "ignore"):
        raise ValueError("expect_mtoon must be all, any or ignore")
    found = _Findings()
    extensions = document.get("extensions") or {}
    nodes = len(document.get("nodes", []))
    report = {"options": opt}
    required = [name for name in document.get("extensionsRequired", []) if name not in KNOWN_EXTENSIONS and name not in opt["allow_extensions"]]
    if required:
        found.add("warning", "extension_required", "The file requires extensions that VRM loaders may not read: " + ", ".join(required))
    report["extensions_used"] = sorted(document.get("extensionsUsed", []))
    report["images"], report["image_list"] = _check_images(document, binary, opt["max_texture"], found)
    report["meshes"], target_counts = _check_meshes(document, found)
    if "VRMC_vrm" in extensions:
        vrm = extensions["VRMC_vrm"]
        report["vrm_version"] = "1.0 (specVersion %s)" % vrm.get("specVersion", "?")
        meta = vrm.get("meta") or {}
        report["meta"] = {"name": meta.get("name", ""), "authors": len(meta.get("authors") or []), "licenseUrl": bool(meta.get("licenseUrl"))}
        if not meta.get("name") or not meta.get("authors") or not meta.get("licenseUrl"):
            found.add("warning", "meta_incomplete", "Meta lacks a name, an author or a licence URL (all three are required)")
        report["humanoid"] = _check_humanoid(vrm, nodes, found)
        report["materials"] = _check_materials(document, opt["expect_mtoon"], found)
        report["springs"] = _check_springs(extensions.get("VRMC_springBone") or {}, nodes, found)
        report["expressions"] = _check_expressions(vrm, document, target_counts, opt["expect_expressions"], found)
        look = vrm.get("lookAt") or {}
        offset = look.get("offsetFromHeadBone")
        report["look_at"] = {"type": look.get("type"), "offsetFromHeadBone": offset,
                             "range_maps": sorted(k for k in look if k.startswith("rangeMap"))}
        if offset is None:
            found.add("warning", "lookat_missing", "No look-at offset; the first-person and gaze origin fall back to the head bone")
        elif offset[2] < 0 or offset[1] < 0:
            found.add("warning", "lookat_axis", "Look-at offset %s lies behind or below the head bone; check the axes "
                      "(VRM is Y up and the model faces +Z)" % [round(float(v), 4) for v in offset])
        first = (vrm.get("firstPerson") or {}).get("meshAnnotations") or []
        counts = {}
        for item in first:
            counts[item.get("type", "?")] = counts.get(item.get("type", "?"), 0) + 1
            if not isinstance(item.get("node"), int) or not 0 <= item["node"] < nodes:
                found.add("error", "firstperson_node", "A first-person annotation points to a node that does not exist")
        report["first_person"] = counts
        report["node_constraints"] = sum(1 for n in document.get("nodes", []) if "VRMC_node_constraint" in (n.get("extensions") or {}))
    elif "VRM" in extensions:
        report["vrm_version"] = "0.x"
        report.update(_check_vrm0(extensions["VRM"], document, opt["expect_mtoon"], found))
    else:
        report["vrm_version"] = None
        found.add("error", "not_vrm", "The file has no VRM extension; it is a plain glTF")
    counts = {level: sum(1 for f in found.items if f["level"] == level) for level in ("error", "warning", "info")}
    report["summary"] = {"errors": counts["error"], "warnings": counts["warning"], "infos": counts["info"],
                         "codes": sorted({f["code"] for f in found.items if f["level"] != "info"})}
    report["findings"] = found.items
    return report


def check_file(path, options=None):
    data = Path(path).read_bytes()
    document, binary = read_glb(data)
    report = check_document(document, binary, options)
    report["input"] = {"name": Path(path).name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    return report


def _new_output(path):
    path = Path(path).expanduser()
    if path.exists() or path.is_symlink():
        raise ValueError("Refusing to overwrite an existing output: " + path.name)
    path = path.resolve()
    if not path.parent.is_dir():
        raise ValueError("Output parent directory must already exist")
    return path


def _write_report(path, report):
    with Path(path).open("x", encoding="utf-8", newline="\n") as output:
        json.dump(report, output, indent=2, ensure_ascii=False, allow_nan=False)
        output.write("\n")


def _parser():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    sub = commands.add_parser("check")
    sub.add_argument("--input", required=True, type=Path)
    sub.add_argument("--report", required=True, type=Path)
    sub.add_argument("--max-texture", type=int)
    sub.add_argument("--expect-mtoon", choices=("all", "any", "ignore"))
    sub.add_argument("--expect-expressions", nargs="*")
    sub.add_argument("--allow-extension", dest="allow_extensions", nargs="+")
    return parser


def main(argv=None):
    if argv is None:
        argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    args = _parser().parse_args(argv)
    report_path = None
    try:
        report_path = _new_output(args.report)
        source = args.input.expanduser().resolve()
        if not source.is_file():
            raise ValueError("Input file not found: " + source.name)
        if source == report_path:
            raise ValueError("Report must differ from input")
        options = {key: getattr(args, key) for key in ("max_texture", "expect_mtoon", "expect_expressions", "allow_extensions")}
        report = check_file(source, options)
        problems = report["summary"]["errors"] + report["summary"]["warnings"]
        report.update({"schema": REPORT_SCHEMA, "command": "check", "unverified": list(UNVERIFIED),
                       "status": "completed_with_findings" if problems else "completed"})
        code = 2 if problems else 0
        _write_report(report_path, report)
        print(json.dumps({"command": "check", "status": report["status"], "summary": report["summary"],
                          "report": report_path.name, "exit_code": code}, ensure_ascii=False))
        return code
    except Exception as error:
        report = {"schema": REPORT_SCHEMA, "command": args.command, "status": "error",
                  "error_type": type(error).__name__, "message": str(error)}
        if report_path is not None and not report_path.exists():
            try:
                _write_report(report_path, report)
            except OSError:
                pass
        print(json.dumps(report, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
