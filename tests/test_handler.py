import pytest

from rmm.mod.handler import (
    read_file_contents,
    read_mod,
    find_about_xml,
    find_steam_publisher_id,
)


@pytest.mark.asyncio
async def test_read_file_contents():
    contents = await read_file_contents("tests/test_mods/About/About.xml")
    assert (
        contents
        == """<?xml version="1.0" encoding="utf-8"?>
<ModMetaData>
    <packageId>test.package.id</packageId>
    <name>Test Mod</name>
    <supportedVersions>
        <li>1.2.3</li>
        <li>1.2.4</li>
    </supportedVersions>
    <author>Test Author</author>
    <url>https://test.url</url>
    <description>Test Description</description>
    <loadAfter>
        <li>test.package.id2</li>
    </loadAfter>
    <loadBefore>
        <li>test.package.id3</li>
    </loadBefore>
    <incompatibleWith>
        <li>test.package.id4</li>
    </incompatibleWith>
    <modDependencies>
        <li>
            <packageId>test.package.id5</packageId>
            <displayName>Test Mod 5</displayName>
            <steamWorkshopUrl>https://test.url5</steamWorkshopUrl>
            <downloadUrl>https://test.url5/download</downloadUrl>
        </li>
        <li>
            <packageId>test.package.id6</packageId>
            <displayName>Test Mod 6</displayName>
            <steamWorkshopUrl>https://test.url6</steamWorkshopUrl>
            <downloadUrl>https://test.url6/download</downloadUrl>
        </li>
    </modDependencies>
</ModMetaData>
"""
    )
