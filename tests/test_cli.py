"""Tests for NiriMod CLI argument handling."""

from __future__ import annotations

import unittest
import pytest

pytest.importorskip("gi")

from gi.repository import GLib
from nirimod.__main__ import NiriModApp


class TestCLIArguments(unittest.TestCase):
    def test_cli_config_option_handling(self):
        app = NiriModApp()
        variant_dict = GLib.VariantDict.new()
        variant_dict.insert_value(
            "config", GLib.Variant.new_string("/custom/path/config.kdl")
        )

        ret = app.do_handle_local_options(variant_dict)
        self.assertEqual(ret, -1)
        self.assertEqual(
            getattr(app, "_cli_config_path", None), "/custom/path/config.kdl"
        )

    def test_cli_version_option_handling(self):
        app = NiriModApp()
        variant_dict = GLib.VariantDict.new()
        variant_dict.insert_value("version", GLib.Variant.new_boolean(True))

        ret = app.do_handle_local_options(variant_dict)
        self.assertEqual(ret, 0)
