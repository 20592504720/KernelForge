"""Bounded UTF-8 Android manifest parsing; DTDs and entities are not supported."""
import xml.etree.ElementTree as ET
from pathlib import Path

MAX_XML_BYTES = 2 * 1024 * 1024
MAX_XML_DEPTH = 32
MAX_XML_ELEMENTS = 20000


class ManifestXMLerror(ValueError):
    pass


class _BoundedTree(ET.TreeBuilder):
    def __init__(self):
        super().__init__()
        self.depth = 0
        self.count = 0

    def start(self, tag, attrs):
        self.depth += 1
        self.count += 1
        if self.depth > MAX_XML_DEPTH or self.count > MAX_XML_ELEMENTS:
            raise ManifestXMLerror("manifest XML structure exceeds resource budget")
        return super().start(tag, attrs)

    def end(self, tag):
        self.depth -= 1
        return super().end(tag)

    def doctype(self, name, pubid, system):
        raise ManifestXMLerror("manifest DTDs and entities are forbidden")


def parse_manifest_xml(value):
    if isinstance(value, bytes):
        if len(value) > MAX_XML_BYTES:
            raise ManifestXMLerror("manifest XML exceeds byte budget")
        try:
            value = value.decode("utf-8-sig")
        except UnicodeError as exc:
            raise ManifestXMLerror("manifest must be UTF-8") from exc
    if not isinstance(value, str) or len(value) > MAX_XML_BYTES:
        raise ManifestXMLerror("invalid manifest XML or byte budget exceeded")
    try:
        if len(value.encode("utf-8")) > MAX_XML_BYTES:
            raise ManifestXMLerror("manifest XML exceeds byte budget")
    except UnicodeError as exc:
        raise ManifestXMLerror("manifest must be UTF-8") from exc
    if "\0" in value or any(x in value.upper() for x in ("<!DOCTYPE", "<!ENTITY")):
        raise ManifestXMLerror("manifest DTDs and entities are forbidden")
    try:
        parser = ET.XMLParser(target=_BoundedTree())
        parser.feed(value)
        return parser.close()
    except ET.ParseError as exc:
        raise ManifestXMLerror("invalid manifest XML") from exc


def read_manifest_xml(path: Path):
    with Path(path).open("rb") as stream:
        return parse_manifest_xml(stream.read(MAX_XML_BYTES + 1))
