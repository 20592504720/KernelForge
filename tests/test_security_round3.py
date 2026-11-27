"""Offline negative tests for manifest parser and HTTPS metadata boundary."""
import io
import unittest
from http.client import HTTPMessage
from unittest.mock import patch
from urllib.request import Request

from kernelforge.http_safety import (
    MetadataURLerror,
    _OriginRedirect,
    open_metadata,
    read_bounded,
)
from kernelforge.versions import releases
from kernelforge.xml_safety import ManifestXMLerror, parse_manifest_xml


class ManifestTests(unittest.TestCase):
    def test_utf8_and_valid_xml(self):
        self.assertEqual(parse_manifest_xml(b"\xef\xbb\xbf<manifest/>").tag, "manifest")

    def test_dtd_and_entities(self):
        for value in ('<!DOCTYPE manifest><manifest/>',
                      '<!DOCTYPE manifest [<!ENTITY demo "fixture">]><manifest>&demo;</manifest>',
                      '<!doctype manifest><manifest/>'):
            with self.subTest(value=value), self.assertRaises(ManifestXMLerror):
                parse_manifest_xml(value)

    def test_utf16_rejected(self):
        with self.assertRaises(ManifestXMLerror):
            parse_manifest_xml("<manifest/>".encode("utf-16"))

    def test_byte_limit(self):
        with patch("kernelforge.xml_safety.MAX_XML_BYTES", 20), self.assertRaisesRegex(ManifestXMLerror, "budget"):
            parse_manifest_xml("<manifest>" + "x"*20 + "</manifest>")

    def test_depth_limit(self):
        with patch("kernelforge.xml_safety.MAX_XML_DEPTH", 3), self.assertRaisesRegex(ManifestXMLerror, "structure"):
            parse_manifest_xml("<a><b><c><d/></c></b></a>")

    def test_element_limit(self):
        with patch("kernelforge.xml_safety.MAX_XML_ELEMENTS", 3), self.assertRaisesRegex(ManifestXMLerror, "structure"):
            parse_manifest_xml("<a><b/><c/><d/></a>")


class NetworkTests(unittest.TestCase):
    def test_initial_origin_rejected_before_connection(self):
        for url in ("http://api.github.com/x", "https://other.invalid/x",
                    "https://user@api.github.com/x", "https://api.github.com:444/x",
                    "https://api.github.com/x#fragment", "https://api.github.com/x?secret=x"):
            with self.subTest(url=url), patch("kernelforge.http_safety.build_opener") as opener:
                with self.assertRaises(MetadataURLerror):
                    open_metadata(Request(url), host="api.github.com", timeout=1)
                opener.assert_not_called()

    def test_redirect_to_other_origin_refused(self):
        request = Request("https://api.github.com/repos/example/project")
        handler = _OriginRedirect("api.github.com", False)
        with self.assertRaises(MetadataURLerror):
            handler.redirect_request(request, io.BytesIO(), 302, "", HTTPMessage(),
                                     "https://other.invalid/x")

    def test_same_origin_redirect_allowed(self):
        request = Request("https://api.github.com/repos/example/project")
        handler = _OriginRedirect("api.github.com", False)
        new = handler.redirect_request(request, io.BytesIO(), 302, "", HTTPMessage(),
                                       "https://api.github.com/repos/example/new")
        if new is None:
            self.fail("same-origin redirect unexpectedly refused")
        self.assertEqual(new.full_url, "https://api.github.com/repos/example/new")

    def test_bounded_response(self):
        self.assertEqual(read_bounded(io.BytesIO(b"ok"), 2), b"ok")
        with self.assertRaises(MetadataURLerror):
            read_bounded(io.BytesIO(b"too large"), 2)

    def test_release_repository_identity(self):
        with patch("kernelforge.versions.open_metadata") as opener:
            with self.assertRaises(ValueError):
                releases("https://github.com/owner/repo/extra")
            opener.assert_not_called()

    def test_release_response_rejects_non_object_rows(self):
        with patch("kernelforge.versions.open_metadata", return_value=io.BytesIO(b"[1]")), self.assertRaisesRegex(ValueError, "invalid release API response"):
            releases("https://github.com/owner/repo")


if __name__ == "__main__":
    unittest.main()
