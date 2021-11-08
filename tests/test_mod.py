import pytest
import os
import tempfile
import rmm.core as core
import pathlib as pl

test_mod_about_xml = """<?xml version="1.0" encoding="utf-8"?>
<ModMetaData>
    <name>Test Mod</name>
    <author>Spoons</author>
    <url>test.com</url>
    <supportedVersions>
        <li>1.0</li>
        <li>1.1</li>
        <li>1.2</li>
        <li>1.3</li>
    </supportedVersions>
<description>
</description>
<packageId>spoons.test</packageId>
</ModMetaData>
"""

test_mod_file_id = "115251734"


@pytest.fixture
def test_create_mod_dir():
    with tempfile.TemporaryDirectory() as path:
        prev_path = os.getcwd()
        os.chdir(path)

        folders = ["1.1", "1.2", "1.3", "About", "Assemblies", "Defs", "Languages"]
        for n in folders:
            os.mkdir(n)

        with open("About/About.xml", "w") as f:
            f.write(test_mod_about_xml)

        with open("About/PublishedFileId.txt", "w") as f:
            f.write(test_mod_file_id)

        os.chdir(prev_path)
        yield path


def test_create_mod(test_create_mod_dir):
    mod_dir = test_create_mod_dir
    test_mod = core.Mod.create_from_path(mod_dir)
    assert test_mod.name == "Test Mod"
    assert test_mod.author == "Spoons"
    assert test_mod.versions == ["1.0", "1.1", "1.2", "1.3"]
    assert test_mod.fp == mod_dir
