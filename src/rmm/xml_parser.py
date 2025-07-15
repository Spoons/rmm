# mod_xml_parser.py
import xml.etree.ElementTree as ET
from pathlib import Path


class NoAboutXMLFile(Exception):
    pass


class NoPackageId(Exception):
    pass


def find_about_xml(path: Path) -> Path:
    """Find the About.xml file in the given path."""
    matches = list(path.glob("About/[Aa][Bb][Oo][Uu][Tt].[Xx][Mm][Ll]"))
    if not matches:
        raise NoAboutXMLFile(str(path))
    return matches[0]


def parse_tree(file_path: Path) -> ET.ElementTree:
    """Parse the XML file and return the root element."""
    return ET.parse(file_path)


def extract_packageid(root: ET.Element) -> str:
    """Extract the package ID from the XML root element."""
    package_id = root.find("packageId")
    if package_id is None or not package_id.text:
        raise NoPackageId()
    return package_id.text.lower()


def read_steamid(path: Path) -> int:
    """Read the Steam ID from the PublishedFileId.txt file."""
    file_content = (path / "About" / "PublishedFileId.txt").read_text().strip()
    return int(file_content)
