import pytest

from rmm.mod.parser import handle_error, parse_xml_field, parse_xml
from rmm.mod import read_mod
import xml.etree.ElementTree as ElementTree
from pathlib import Path


@pytest.fixture
def root():
    return ElementTree.fromstring("<outer><data>data</data></outer>")


RIMHUD_ABOUT_XML = """<?parser version="1.0" encoding="utf-8"?>
<ModMetaData>
  <packageId>Jaxe.RimHUD</packageId>
  <name>RimHUD</name>
  <author>Jaxe</author>
  <description>modxml Version: {ReleaseVersion}\n\nRimHUD is a UI mod that displays detailed information about a selected character or creature. The HUD display is integrated into the inspect pane which can be resized to fit the additional information. Alternatively, the HUD can display a separate floating window and can be docked to any position on the screen.\n\nVisual warnings will appear if a pawn has any life-threatening conditions, has wounds that need tending to, or is close to a mental breakdown.</description>
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


def test_parse_xml():
    assert parse_xml(RIMHUD_ABOUT_XML).unwrap().package_id == "Jaxe.RimHUD"


def test_mod_dependencies():
    deps = parse_xml(RIMHUD_ABOUT_XML).unwrap().dependencies
    assert deps[0].package_id == "brrainz.harmony"
    assert deps[0].name == "Harmony"
    assert deps[0].workshop_url == "steam://url/CommunityFilePage/2009463077"
    assert (
        deps[0].download_url
        == "https://github.com/pardeike/HarmonyRimWorld/releases/latest"
    )
