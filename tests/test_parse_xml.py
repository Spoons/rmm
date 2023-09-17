import pytest

from rmm.Mod.parse_xml import handle_error, parse_xml_field, parse_xml, read_mod
from rmm.error import Ok, Err, Result
import xml.etree.ElementTree as ElementTree
from pathlib import Path


@pytest.fixture
def root():
    return ElementTree.fromstring("<outer><data>data</data></outer>")


@pytest.fixture
def rimhud_about_xml_file():
    mod_xml = """<?xml version="1.0" encoding="utf-8"?>
    <ModMetaData>
      <packageId>Jaxe.RimHUD</packageId>
      <name>RimHUD</name>
      <author>Jaxe</author>
      <description>Mod Version: {ReleaseVersion}\n\nRimHUD is a UI mod that displays detailed information about a selected character or creature. The HUD display is integrated into the inspect pane which can be resized to fit the additional information. Alternatively, the HUD can display a separate floating window and can be docked to any position on the screen.\n\nVisual warnings will appear if a pawn has any life-threatening conditions, has wounds that need tending to, or is close to a mental breakdown.</description>
      <supportedVersions>
        <li>1.1</li>
        <li>1.2</li>
        <li>1.3</li>
        <li>1.4</li>
      </supportedVersions>
      <modDependencies>
        <li>
          <packageId>brrainz.harmony</packageId>
          <displayName>Harmony</displayName>
          <steamWorkshopUrl>steam://url/CommunityFilePage/2009463077</steamWorkshopUrl>
          <downloadUrl>https://github.com/pardeike/HarmonyRimWorld/releases/latest</downloadUrl>
        </li>
      </modDependencies>
      <loadAfter>
        <li>brrainz.harmony</li>
      </loadAfter>
    </ModMetaData>"""
    mod_xml_path = Path("/tmp/mod.xml")
    mod_xml_path.write_text(mod_xml)
    return mod_xml_path


def test_handle_error():
    assert handle_error("field", "result", True).is_error() == False
    assert handle_error("field", None, True).is_error() == True


def test_parse_xml_field_required_fail(root):
    assert parse_xml_field(root, "field").is_error() == True


def test_parse_xml_field_required_pass(root):
    assert parse_xml_field(root, "data").is_error() == False
    assert parse_xml_field(root, "data").unwrap() == "data"


def test_parse_xml_field_optional_pass(root):
    assert parse_xml_field(root, "data", False).is_error() == False
    assert parse_xml_field(root, "data", False).unwrap() == "data"


def test_parse_xml_field_optional_fail(root):
    assert parse_xml_field(root, "field", False).is_error() == False
    assert parse_xml_field(root, "field", False).unwrap() == None


def test_parse_xml_list_required_fail(root):
    assert parse_xml_field(root, "field").is_error() == True


def test_parse_xml_list_required_pass(root):
    assert parse_xml_field(root, "data").is_error() == False
    assert parse_xml_field(root, "data").unwrap() == "data"


def test_parse_xml_list_optional_pass(root):
    assert parse_xml_field(root, "data", False).is_error() == False
    assert parse_xml_field(root, "data", False).unwrap() == "data"


def test_parse_xml(rimhud_about_xml_file):
    assert parse_xml(rimhud_about_xml_file).package_id == "Jaxe.RimHUD"


def test_read_mod_fail(rimhud_about_xml_file):
    assert read_mod(Path("/fakepath")).is_error() == True
