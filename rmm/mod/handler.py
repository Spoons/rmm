import typing as t
from pathlib import Path

import aiofiles
import asyncio
from rmm.error import Err, Ok, Result
from rmm.mod.parser import parse_xml
from rmm.mod.mod import Mod

ABOUT_XML_REGEX = "[Aa]bout/[Aa][Bb][Oo][Uu][Tt].[Xx][Mm][Ll]"
PUBLISHED_FILE_ID_REGEX = "[Aa]bout/[Pp]ublished[Ff]ile[Ii][Dd].[Tt][Xx][Tt]"


async def read_file_contents(path: Path) -> t.Optional[str]:
    try:
        async with aiofiles.open(path, "r") as f:
            return await f.read()
    except FileNotFoundError:
        return None


async def read_mod(path: Path) -> Result:
    about_xml = find_about_xml(path)
    if not about_xml:
        return Err(f"No About.xml found in {path}")

    about_xml_contents = await read_file_contents(about_xml)
    if not about_xml_contents:
        return Err(f"Unable to read About.xml at {about_xml}")

    steam_id_file = find_steam_publisher_id(path)
    if not steam_id_file:
        return Err(f"No PublishedFileID.txt found in {path}")

    steam_id_file_contents = await read_file_contents(steam_id_file)
    if not steam_id_file_contents:
        return Err(f"Unable to read PublishedFileID.txt at {steam_id_file}")

    mod = parse_xml(about_xml_contents)
    if mod.is_err:
        return Err("Unable to parse About.xml" + mod.unwrap())

    mod = Mod(steam_id_file_contents, mod.unwrap())

    return Ok(mod)


def find_about_xml(path: Path) -> t.Optional[Path]:
    # Use glob to get the case-insensitive About.parser path
    matches = list(path.glob(ABOUT_XML_REGEX))
    return matches[0] if matches else None


def find_steam_publisher_id(path: Path) -> t.Optional[Path]:
    matches = list(path.glob(PUBLISHED_FILE_ID_REGEX))
    return matches[0] if matches else None


if __name__ == "__main__":
    mod = asyncio.run(read_mod(Path("/games/rimworld-dev/game/Mods/jaxe.rimhud")))
    print(mod.unwrap())
