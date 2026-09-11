from __future__ import annotations

import os
import re
import uuid
from copy import deepcopy
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape
from zipfile import BadZipFile, ZIP_DEFLATED, ZIP_STORED, ZipFile

from lxml import etree

from .common import natural_key, sha256_bytes, sha256_file, timestamp, write_json_atomic


HP_NS = "http://www.hancom.co.kr/hwpml/2011/paragraph"
HS_NS = "http://www.hancom.co.kr/hwpml/2011/section"
HH_NS = "http://www.hancom.co.kr/hwpml/2011/head"
OPF_NS = "http://www.idpf.org/2007/opf/"
HP = f"{{{HP_NS}}}"
HS = f"{{{HS_NS}}}"
HH = f"{{{HH_NS}}}"
NS = {"hp": HP_NS, "hs": HS_NS, "hh": HH_NS, "opf": OPF_NS}
REFERENCE_ATTRS = ("binaryItemIDRef", "binItemIDRef", "bindataIDRef")

for prefix, uri in (("hp", HP_NS), ("hs", HS_NS), ("hh", HH_NS), ("opf", OPF_NS)):
    etree.register_namespace(prefix, uri)


def _xml(data: bytes) -> etree._Element:
    return etree.fromstring(
        data, parser=etree.XMLParser(remove_blank_text=False, recover=False)
    )


def _section_key(name: str) -> int:
    match = re.search(r"section(\d+)\.xml$", name)
    return int(match.group(1)) if match else 10**9


def _masterpage_key(name: str) -> int:
    match = re.search(r"masterpage(\d+)\.xml$", name)
    return int(match.group(1)) if match else 10**9


def _local_name(element: etree._Element) -> str:
    return etree.QName(element).localname


def _manifest(root: etree._Element) -> dict[str, tuple[str, str]]:
    result: dict[str, tuple[str, str]] = {}
    for item in root.xpath(".//opf:item", namespaces=NS):
        item_id = item.get("id")
        href = item.get("href")
        if item_id and href:
            result[item_id] = (href, item.get("media-type") or "application/octet-stream")
    return result


def _referenced_hashes(
    root: etree._Element,
    archive: ZipFile,
    names: set[str],
    manifest: dict[str, tuple[str, str]],
) -> tuple[list[str], list[str]]:
    hashes: list[str] = []
    missing: list[str] = []
    for node in root.iter():
        for attribute in REFERENCE_ATTRS:
            item_id = node.get(attribute)
            if not item_id:
                continue
            record = manifest.get(item_id)
            if record is None:
                missing.append(f"{attribute}:{item_id}:manifest")
                continue
            href = record[0]
            if href not in names:
                missing.append(f"{attribute}:{item_id}:{href}")
                continue
            hashes.append(sha256_bytes(archive.read(href)))
    return hashes, missing


def inspect_hwpx(path: Path) -> dict[str, Any]:
    path = path.expanduser().resolve()
    errors: list[str] = []
    warnings: list[str] = []
    result: dict[str, Any] = {
        "path": str(path),
        "size": path.stat().st_size if path.is_file() else 0,
        "sha256": sha256_file(path) if path.is_file() else None,
        "sections": 0,
        "section_text_hashes": [],
        "section_image_hashes": [],
        "tables": 0,
        "pictures": 0,
        "equations": 0,
        "bindata_hashes": [],
        "missing_references": [],
        "errors": errors,
        "warnings": warnings,
        "ok": False,
    }
    if not path.is_file():
        errors.append("file_not_found")
        return result
    try:
        with ZipFile(path) as archive:
            bad_member = archive.testzip()
            if bad_member:
                errors.append(f"crc_error:{bad_member}")
            infos = archive.infolist()
            names = {info.filename for info in infos}
            required = {
                "mimetype",
                "Contents/content.hpf",
                "Contents/header.xml",
            }
            missing_required = sorted(required - names)
            errors.extend(f"missing_member:{name}" for name in missing_required)
            if infos:
                if infos[0].filename != "mimetype":
                    errors.append("mimetype_not_first")
                elif infos[0].compress_type != ZIP_STORED:
                    errors.append("mimetype_not_stored")
            if "mimetype" in names:
                mime = archive.read("mimetype").decode("ascii", errors="replace").strip()
                if mime != "application/hwp+zip":
                    errors.append(f"unexpected_mimetype:{mime}")
            for name in sorted(n for n in names if n.lower().endswith((".xml", ".hpf"))):
                try:
                    _xml(archive.read(name))
                except Exception as exc:
                    errors.append(f"xml_error:{name}:{exc}")
            if errors:
                return result

            content = _xml(archive.read("Contents/content.hpf"))
            manifest = _manifest(content)
            supported_hrefs = {
                "Contents/header.xml",
                "settings.xml",
            }
            unsupported = sorted(
                href
                for href, _media in manifest.values()
                if href not in supported_hrefs
                and not href.startswith("BinData/")
                and not (
                    href.startswith("Contents/section") and href.endswith(".xml")
                )
                and not (
                    href.startswith("Contents/masterpage") and href.endswith(".xml")
                )
            )
            errors.extend(f"unsupported_manifest_resource:{href}" for href in unsupported)
            masterpage_hashes: dict[str, list[str]] = {}
            for item_id, (href, _media) in manifest.items():
                if href.startswith("Contents/masterpage") and href.endswith(".xml"):
                    if href not in names:
                        errors.append(f"missing_masterpage:{item_id}:{href}")
                        continue
                    hashes, missing = _referenced_hashes(
                        _xml(archive.read(href)), archive, names, manifest
                    )
                    masterpage_hashes[item_id] = hashes
                    errors.extend(f"{href}:{entry}" for entry in missing)

            sections = sorted(
                (
                    name
                    for name in names
                    if name.startswith("Contents/section") and name.endswith(".xml")
                ),
                key=_section_key,
            )
            if not sections:
                errors.append("no_sections")
                return result
            result["sections"] = len(sections)
            for name in sections:
                root = _xml(archive.read(name))
                text = "".join(
                    str(value)
                    for value in root.xpath(
                        ".//hp:t/text()[not(ancestor::hp:header) and not(ancestor::hp:footer)]",
                        namespaces=NS,
                    )
                )
                result["section_text_hashes"].append(
                    sha256_bytes(text.encode("utf-8"))
                )
                direct_hashes, missing = _referenced_hashes(
                    root, archive, names, manifest
                )
                errors.extend(f"{name}:{entry}" for entry in missing)
                image_hashes = list(direct_hashes)
                for ref in root.xpath(".//hp:masterPage[@idRef]", namespaces=NS):
                    item_id = ref.get("idRef")
                    if item_id not in masterpage_hashes:
                        errors.append(f"{name}:missing_masterpage_ref:{item_id}")
                    else:
                        image_hashes.extend(masterpage_hashes[item_id])
                result["section_image_hashes"].append(image_hashes)
                result["tables"] += len(
                    root.xpath(
                        ".//hp:tbl[not(ancestor::hp:header) and not(ancestor::hp:footer)]",
                        namespaces=NS,
                    )
                )
                result["pictures"] += len(
                    root.xpath(
                        ".//hp:pic[not(ancestor::hp:header) and not(ancestor::hp:footer)]",
                        namespaces=NS,
                    )
                )
                result["equations"] += len(
                    root.xpath(
                        ".//hp:equation[not(ancestor::hp:header) and not(ancestor::hp:footer)]",
                        namespaces=NS,
                    )
                )

            bindata_names = sorted(
                name for name in names if name.startswith("BinData/") and not name.endswith("/")
            )
            result["bindata_hashes"] = sorted(
                sha256_bytes(archive.read(name)) for name in bindata_names
            )
            result["missing_references"] = [
                item for item in errors if "missing" in item
            ]
    except BadZipFile:
        errors.append("not_a_zip")
    except Exception as exc:
        errors.append(f"inspection_error:{type(exc).__name__}:{exc}")
    result["ok"] = not errors
    return result


def _first_desc(root: etree._Element, tag: str) -> etree._Element | None:
    found = root.xpath(f".//hh:{tag}", namespaces=NS)
    return found[0] if found else None


def _children(container: etree._Element | None) -> list[etree._Element]:
    return [] if container is None else [item for item in container if isinstance(item.tag, str)]


def _max_numeric_id(container: etree._Element | None) -> int:
    values = [
        int(item.get("id"))
        for item in _children(container)
        if (item.get("id") or "").isdigit()
    ]
    return max(values, default=-1)


def _remap_idrefs(root: etree._Element, maps: dict[str, dict[str, str]]) -> None:
    attribute_map = {
        "borderFillIDRef": "borderFill",
        "charPrIDRef": "charPr",
        "paraPrIDRef": "paraPr",
        "styleIDRef": "style",
        "nextStyleIDRef": "style",
        "tabPrIDRef": "tabPr",
        "numberingIDRef": "numbering",
        "bulletIDRef": "bullet",
    }
    for node in root.iter():
        for attribute, map_name in attribute_map.items():
            old = node.get(attribute)
            if old in maps.get(map_name, {}):
                node.set(attribute, maps[map_name][old])


def _merge_fontfaces(
    target: etree._Element, source: etree._Element
) -> dict[str, dict[str, str]]:
    mapping: dict[str, dict[str, str]] = {}
    target_faces = _first_desc(target, "fontfaces")
    source_faces = _first_desc(source, "fontfaces")
    if target_faces is None or source_faces is None:
        return mapping
    by_language = {
        face.get("lang") or "": face
        for face in target_faces.xpath("./hh:fontface", namespaces=NS)
    }
    for source_face in source_faces.xpath("./hh:fontface", namespaces=NS):
        language = source_face.get("lang") or ""
        target_face = by_language.get(language)
        if target_face is None:
            clone = deepcopy(source_face)
            target_faces.append(clone)
            by_language[language] = clone
            mapping[language] = {
                item.get("id"): item.get("id")
                for item in clone.xpath("./hh:font", namespaces=NS)
                if item.get("id") is not None
            }
            continue
        existing: dict[tuple[str | None, str | None, str | None], str] = {}
        maximum = -1
        for font in target_face.xpath("./hh:font", namespaces=NS):
            old_id = font.get("id")
            if old_id and old_id.isdigit():
                maximum = max(maximum, int(old_id))
            if old_id is not None:
                existing[(font.get("face"), font.get("type"), font.get("isEmbedded"))] = old_id
        language_map: dict[str, str] = {}
        for font in source_face.xpath("./hh:font", namespaces=NS):
            old_id = font.get("id")
            if old_id is None:
                continue
            key = (font.get("face"), font.get("type"), font.get("isEmbedded"))
            if key in existing:
                language_map[old_id] = existing[key]
                continue
            maximum += 1
            clone = deepcopy(font)
            clone.set("id", str(maximum))
            target_face.append(clone)
            existing[key] = str(maximum)
            language_map[old_id] = str(maximum)
        target_face.set("fontCnt", str(len(target_face.xpath("./hh:font", namespaces=NS))))
        mapping[language] = language_map
    target_faces.set("itemCnt", str(len(target_faces.xpath("./hh:fontface", namespaces=NS))))
    return mapping


def _remap_fontrefs(root: etree._Element, maps: dict[str, dict[str, str]]) -> None:
    for font_ref in root.xpath(".//hh:fontRef", namespaces=NS):
        for language, id_map in maps.items():
            attribute = language.lower()
            old = font_ref.get(attribute)
            if old in id_map:
                font_ref.set(attribute, id_map[old])


def _append_header_container(
    target: etree._Element,
    source: etree._Element,
    container_name: str,
    child_name: str,
    map_name: str,
    id_maps: dict[str, dict[str, str]],
    font_maps: dict[str, dict[str, str]],
) -> None:
    target_container = _first_desc(target, container_name)
    source_container = _first_desc(source, container_name)
    if target_container is None or source_container is None:
        return
    next_id = _max_numeric_id(target_container) + 1
    children = source_container.xpath(f"./hh:{child_name}", namespaces=NS)
    id_map = id_maps.setdefault(map_name, {})
    for child in children:
        old_id = child.get("id")
        if old_id is not None:
            id_map[old_id] = str(next_id)
            next_id += 1
    for child in children:
        old_id = child.get("id")
        if old_id is None:
            continue
        clone = deepcopy(child)
        clone.set("id", id_map[old_id])
        _remap_fontrefs(clone, font_maps)
        _remap_idrefs(clone, id_maps)
        target_container.append(clone)
    target_container.set("itemCnt", str(len(_children(target_container))))


def _merge_header(target: etree._Element, source: etree._Element) -> dict[str, dict[str, str]]:
    maps: dict[str, dict[str, str]] = {}
    font_maps = _merge_fontfaces(target, source)
    for spec in (
        ("borderFills", "borderFill", "borderFill"),
        ("tabProperties", "tabPr", "tabPr"),
        ("charProperties", "charPr", "charPr"),
        ("numberings", "numbering", "numbering"),
        ("bullets", "bullet", "bullet"),
        ("paraProperties", "paraPr", "paraPr"),
        ("styles", "style", "style"),
    ):
        _append_header_container(target, source, *spec, maps, font_maps)
    return maps


def _media_type(path: str) -> str:
    return {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".bmp": "image/bmp",
        ".svg": "image/svg+xml",
    }.get(Path(path).suffix.lower(), "application/octet-stream")


def _collect_bindata(
    source: Path, counter: int
) -> tuple[dict[str, str], list[tuple[str, bytes, str, str]], int]:
    with ZipFile(source) as archive:
        names = archive.namelist()
        manifest = _manifest(_xml(archive.read("Contents/content.hpf")))
        by_href: dict[str, list[tuple[str, str]]] = {}
        for item_id, (href, media) in manifest.items():
            by_href.setdefault(href, []).append((item_id, media))
        mapping: dict[str, str] = {}
        items: list[tuple[str, bytes, str, str]] = []
        for old_href in sorted(
            name for name in names if name.startswith("BinData/") and not name.endswith("/")
        ):
            counter += 1
            records = by_href.get(
                old_href, [(Path(old_href).stem, _media_type(old_href))]
            )
            media = records[0][1]
            new_id = f"img{counter}"
            new_href = f"BinData/{new_id}{Path(old_href).suffix.lower()}"
            for old_id, _old_media in records:
                mapping[old_id] = new_id
            mapping[old_href] = new_href
            items.append((new_href, archive.read(old_href), new_id, media))
    return mapping, items, counter


def _remap_exact_attributes(root: etree._Element, mapping: dict[str, str]) -> None:
    for node in root.iter():
        for attribute, value in list(node.attrib.items()):
            if value in mapping:
                node.set(attribute, mapping[value])


def _renumber_ids(roots: list[etree._Element]) -> None:
    paragraph_id = 1
    table_id = 100000
    object_id = 200000
    z_order = 0
    object_tags = {
        "container", "pic", "rect", "line", "ellipse", "arc", "polygon",
        "curve", "connectLine", "textart", "ole", "equation",
    }
    for root in roots:
        for paragraph in root.xpath(".//hp:p", namespaces=NS):
            paragraph.set("id", str(paragraph_id))
            paragraph_id += 1
        for table in root.xpath(".//hp:tbl", namespaces=NS):
            table.set("id", str(table_id))
            table_id += 1
        for element in root.xpath(".//*[@id or @zOrder]", namespaces=NS):
            if not isinstance(element.tag, str) or _local_name(element) not in object_tags:
                continue
            if element.get("id"):
                element.set("id", str(object_id))
                if element.get("instid") not in (None, "", "0"):
                    element.set("instid", str(object_id))
                object_id += 1
            if element.get("zOrder") is not None:
                element.set("zOrder", str(z_order))
                z_order += 1


def _content_hpf(
    title: str,
    section_count: int,
    binary_items: list[tuple[str, bytes, str, str]],
    masterpages: list[tuple[str, bytes, str, str]],
) -> bytes:
    lines = [
        "<?xml version='1.0' encoding='UTF-8'?>",
        '<opf:package xmlns:opf="http://www.idpf.org/2007/opf/" '
        'xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph" '
        'xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section" '
        'xmlns:hh="http://www.hancom.co.kr/hwpml/2011/head" version="" id="">',
        "  <opf:metadata>",
        f"    <opf:title>{escape(title)}</opf:title>",
        "    <opf:language>ko</opf:language>",
        '    <opf:meta name="creator" content="text">hwp-manage</opf:meta>',
        "  </opf:metadata>",
        "  <opf:manifest>",
        '    <opf:item id="header" href="Contents/header.xml" media-type="application/xml"/>',
    ]
    for href, _data, item_id, media in binary_items:
        lines.append(
            f'    <opf:item id="{escape(item_id)}" href="{escape(href)}" '
            f'media-type="{escape(media)}" isEmbeded="1"/>'
        )
    for href, _data, item_id, media in masterpages:
        lines.append(
            f'    <opf:item id="{escape(item_id)}" href="{escape(href)}" '
            f'media-type="{escape(media)}"/>'
        )
    for index in range(section_count):
        lines.append(
            f'    <opf:item id="section{index}" href="Contents/section{index}.xml" media-type="application/xml"/>'
        )
    lines.extend(
        [
            '    <opf:item id="settings" href="settings.xml" media-type="application/xml"/>',
            "  </opf:manifest>",
            "  <opf:spine>",
            '    <opf:itemref idref="header" linear="yes"/>',
        ]
    )
    lines.extend(
        f'    <opf:itemref idref="section{index}" linear="yes"/>'
        for index in range(section_count)
    )
    lines.extend(["  </opf:spine>", "</opf:package>"])
    return ("\n".join(lines) + "\n").encode("utf-8")


def _write_package(
    base: Path,
    output: Path,
    header: bytes,
    sections: list[bytes],
    content: bytes,
    preview: bytes,
    binary_items: list[tuple[str, bytes, str, str]],
    masterpages: list[tuple[str, bytes, str, str]],
) -> None:
    replacements = {
        "Contents/header.xml": header,
        "Contents/content.hpf": content,
        "Preview/PrvText.txt": preview,
    }
    with ZipFile(base) as source, ZipFile(output, "w", ZIP_DEFLATED) as target:
        target.writestr("mimetype", b"application/hwp+zip", compress_type=ZIP_STORED)
        for name in source.namelist():
            if name == "mimetype" or name.startswith("BinData/"):
                continue
            if name.startswith("Contents/section") and name.endswith(".xml"):
                continue
            if name.startswith("Contents/masterpage") and name.endswith(".xml"):
                continue
            if name in replacements:
                target.writestr(name, replacements[name])
            else:
                target.writestr(name, source.read(name))
        for index, data in enumerate(sections):
            target.writestr(f"Contents/section{index}.xml", data)
        for href, data, _item_id, _media in binary_items + masterpages:
            target.writestr(href, data)


def merge_hwpx(
    inputs: list[Path],
    output: Path,
    *,
    title: str,
    report_path: Path | None = None,
) -> dict[str, Any]:
    inputs = [path.expanduser().resolve() for path in inputs]
    if not inputs:
        raise ValueError("병합할 HWPX가 없습니다.")
    if inputs != sorted(inputs, key=natural_key):
        raise ValueError("입력 파일은 자연 정렬 순서로 전달해야 합니다.")
    before = [inspect_hwpx(path) for path in inputs]
    failures = [item for item in before if not item["ok"]]
    if failures:
        raise ValueError(f"입력 HWPX 검사 실패: {failures}")

    base = inputs[0]
    with ZipFile(base) as archive:
        header_root = _xml(archive.read("Contents/header.xml"))
    section_roots: list[etree._Element] = []
    binary_items: list[tuple[str, bytes, str, str]] = []
    masterpages: list[tuple[str, bytes, str, str]] = []
    binary_counter = 0
    masterpage_counter = 0

    for document_index, source in enumerate(inputs):
        with ZipFile(source) as archive:
            names = archive.namelist()
            content_manifest = _manifest(_xml(archive.read("Contents/content.hpf")))
            if document_index == 0:
                style_maps: dict[str, dict[str, str]] = {}
            else:
                style_maps = _merge_header(
                    header_root, _xml(archive.read("Contents/header.xml"))
                )
            binary_map, new_items, binary_counter = _collect_bindata(
                source, binary_counter
            )
            binary_items.extend(new_items)

            masterpage_map: dict[str, str] = {}
            masterpage_names = sorted(
                (
                    name
                    for name in names
                    if name.startswith("Contents/masterpage") and name.endswith(".xml")
                ),
                key=_masterpage_key,
            )
            for name in masterpage_names:
                old_id = next(
                    (
                        item_id
                        for item_id, (href, _media) in content_manifest.items()
                        if href == name
                    ),
                    Path(name).stem,
                )
                new_id = f"masterpage{masterpage_counter}"
                new_href = f"Contents/{new_id}.xml"
                masterpage_counter += 1
                masterpage_map[old_id] = new_id
                root = _xml(archive.read(name))
                _remap_exact_attributes(root, binary_map)
                _remap_idrefs(root, style_maps)
                masterpages.append(
                    (
                        new_href,
                        etree.tostring(root, encoding="UTF-8", xml_declaration=True),
                        new_id,
                        "application/xml",
                    )
                )

            section_names = sorted(
                (
                    name
                    for name in names
                    if name.startswith("Contents/section") and name.endswith(".xml")
                ),
                key=_section_key,
            )
            for name in section_names:
                root = _xml(archive.read(name))
                _remap_exact_attributes(root, binary_map)
                _remap_idrefs(root, style_maps)
                for reference in root.xpath(".//hp:masterPage[@idRef]", namespaces=NS):
                    old_id = reference.get("idRef")
                    if old_id in masterpage_map:
                        reference.set("idRef", masterpage_map[old_id])
                section_roots.append(root)

    _renumber_ids(section_roots)
    header_root.set("secCnt", str(len(section_roots)))
    header = etree.tostring(header_root, encoding="UTF-8", xml_declaration=True)
    sections = [
        etree.tostring(root, encoding="UTF-8", xml_declaration=True)
        for root in section_roots
    ]
    preview = (
        "\n".join(
            text
            for root in section_roots
            for text in root.xpath(".//hp:t/text()", namespaces=NS)
            if str(text).strip()
        )
        + "\n"
    ).encode("utf-8")
    content = _content_hpf(title, len(sections), binary_items, masterpages)

    output = output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.name}.{uuid.uuid4().hex}.tmp")
    try:
        _write_package(
            base, temporary, header, sections, content, preview, binary_items, masterpages
        )
        after = inspect_hwpx(temporary)
        expected_sections = sum(item["sections"] for item in before)
        expected_text = [value for item in before for value in item["section_text_hashes"]]
        expected_images = [value for item in before for value in item["section_image_hashes"]]
        expected_bindata = sorted(
            value for item in before for value in item["bindata_hashes"]
        )
        conservation = {
            "sections": after["sections"] == expected_sections,
            "section_text": after["section_text_hashes"] == expected_text,
            "section_images": after["section_image_hashes"] == expected_images,
            "bindata": after["bindata_hashes"] == expected_bindata,
            "tables": after["tables"] == sum(item["tables"] for item in before),
            "pictures": after["pictures"] == sum(item["pictures"] for item in before),
            "equations": after["equations"] == sum(item["equations"] for item in before),
        }
        if not after["ok"] or not all(conservation.values()):
            raise RuntimeError(
                f"병합 결과 무결성 검사 실패: ok={after['ok']} conservation={conservation} errors={after['errors']}"
            )
        os.replace(temporary, output)
        after = inspect_hwpx(output)
    finally:
        if temporary.exists():
            temporary.unlink()

    report = {
        "created_at": timestamp(),
        "title": title,
        "inputs": [str(path) for path in inputs],
        "output": str(output),
        "input_count": len(inputs),
        "before": before,
        "after": after,
        "conservation": conservation,
        "passed": after["ok"] and all(conservation.values()),
    }
    if report_path:
        write_json_atomic(report_path, report)
    return report
