from __future__ import annotations

from pathlib import Path
from typing import NamedTuple
from xml.etree import ElementTree
import posixpath
import zipfile


class EpubCover(NamedTuple):
    content: bytes
    extension: str


_IMAGE_EXTENSION_BY_MEDIA_TYPE = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


def _normalize_zip_path(base_path: str, relative_path: str) -> str | None:
    joined = posixpath.normpath(posixpath.join(base_path, relative_path))
    if joined.startswith("../") or joined.startswith("/") or joined == "..":
        return None
    return joined


def _find_root_package_path(archive: zipfile.ZipFile) -> str | None:
    try:
        container_xml = archive.read("META-INF/container.xml")
    except KeyError:
        return None

    try:
        root = ElementTree.fromstring(container_xml)
    except ElementTree.ParseError:
        return None

    for element in root.findall(".//{*}rootfile"):
        full_path = (element.attrib.get("full-path") or "").strip()
        if full_path:
            return full_path
    return None


def _extract_cover_item_path(archive: zipfile.ZipFile, opf_path: str) -> tuple[str, str | None] | None:
    try:
        opf_bytes = archive.read(opf_path)
    except KeyError:
        return None

    try:
        opf_root = ElementTree.fromstring(opf_bytes)
    except ElementTree.ParseError:
        return None

    metadata = opf_root.find(".//{*}metadata")
    manifest = opf_root.find(".//{*}manifest")
    if metadata is None or manifest is None:
        return None

    cover_id = None
    for meta in metadata.findall("{*}meta"):
        if (meta.attrib.get("name") or "").strip().lower() == "cover":
            content = (meta.attrib.get("content") or "").strip()
            if content:
                cover_id = content
                break

    manifest_items: list[dict[str, str]] = []
    for item in manifest.findall("{*}item"):
        manifest_items.append(
            {
                "id": (item.attrib.get("id") or "").strip(),
                "href": (item.attrib.get("href") or "").strip(),
                "media_type": (item.attrib.get("media-type") or "").strip().lower(),
                "properties": (item.attrib.get("properties") or "").strip().lower(),
            }
        )

    cover_item = None
    if cover_id:
        cover_item = next((entry for entry in manifest_items if entry["id"] == cover_id), None)

    if cover_item is None:
        cover_item = next(
            (
                entry
                for entry in manifest_items
                if "cover-image" in entry["properties"] and entry["media_type"].startswith("image/")
            ),
            None,
        )

    if cover_item is None:
        cover_item = next(
            (
                entry
                for entry in manifest_items
                if entry["media_type"].startswith("image/")
                and ("cover" in entry["id"].lower() or "cover" in entry["href"].lower())
            ),
            None,
        )

    if cover_item is None:
        return None

    opf_dir = posixpath.dirname(opf_path)
    resolved = _normalize_zip_path(opf_dir, cover_item["href"])
    if resolved is None:
        return None

    return resolved, cover_item["media_type"] or None


def _derive_image_extension(path_in_archive: str, media_type: str | None) -> str:
    if media_type:
        mapped = _IMAGE_EXTENSION_BY_MEDIA_TYPE.get(media_type.lower())
        if mapped:
            return mapped

    suffix = Path(path_in_archive).suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        return ".jpg" if suffix == ".jpeg" else suffix

    return ".img"


def read_epub_cover(epub_path: Path) -> EpubCover | None:
    if not epub_path.exists() or epub_path.suffix.lower() != ".epub":
        return None

    try:
        with zipfile.ZipFile(epub_path, "r") as archive:
            opf_path = _find_root_package_path(archive)
            if not opf_path:
                return None

            cover_item = _extract_cover_item_path(archive, opf_path)
            if cover_item is None:
                return None

            cover_path_in_archive, media_type = cover_item
            cover_bytes = archive.read(cover_path_in_archive)
            if not cover_bytes:
                return None

            extension = _derive_image_extension(cover_path_in_archive, media_type)
            return EpubCover(content=cover_bytes, extension=extension)
    except (zipfile.BadZipFile, KeyError, OSError):
        return None
