from rmm.Mod.modaboutxml import ModAboutXML, ModDep
from pathlib import Path
import typing as t
import xml.etree.ElementTree as Et
from rmm.error import Ok, Err, Result


def find_about_xml(path: Path) -> t.Optional[Path]:
    # Use glob to get the case-insensitive About.xml path
    matches = list(path.glob("About/[Aa][Bb][Oo][Uu][Tt].[Xx][Mm][Ll]"))
    return matches[0] if matches else None


def get_xml_field(root: Et.ElementTree, field: str) -> t.Optional[str]:
    result = root.find(field)
    try:
        return result.text
    except AttributeError:
        return None


def get_xml_list(root: Et.ElementTree, field: str) -> t.List[str]:
    result = root.find(field)
    try:
        return [n.text for n in result.findall("li")]
    except AttributeError:
        return []


def handle_error(field: str, result: t.Any, required: bool) -> Result:
    if not result and required:
        return Err(f"Unable to parse field: {field}")
    return Ok(result)


def parse_xml_field(root: Et.ElementTree, field, required=True):
    return handle_error(field, get_xml_field(root, field), required)


def parse_xml_list(root: Et.ElementTree, field, required=True):
    return handle_error(field, get_xml_list(root, field), required)


def parse_xml_dependency(element: Et.Element):
    package_id = parse_xml_field(element, "packageId").unwrap()
    display_name = parse_xml_field(element, "displayName").unwrap()
    steam_workshop_url = parse_xml_field(element, "steamWorkshopUrl").unwrap()
    download_url = parse_xml_field(element, "downloadUrl").unwrap()
    return ModDep(package_id, display_name, steam_workshop_url, download_url)


def parse_mod_dependencies(root: Et.ElementTree):
    result = root.find("modDependencies")
    if not result:
        return Ok([])

    deps = []
    for element in result:
        deps.append(parse_xml_dependency(element))
    return Ok(deps)


def parse_xml(path: Path):
    try:
        tree = Et.parse(path)
    except Et.ParseError as e:
        return Err(e)

    package_id = parse_xml_field(tree, "packageId").unwrap()
    before = parse_xml_list(tree, "loadBefore", required=False).unwrap()
    after = parse_xml_list(tree, "loadAfter", required=False).unwrap()
    incompatible = parse_xml_list(tree, "incompatibleWith", required=False).unwrap()
    author = parse_xml_field(tree, "author").unwrap_or("Unknown")
    name = parse_xml_field(tree, "name").unwrap()
    supported_versions = parse_xml_list(tree, "supportedVersions").unwrap()
    dependencies = parse_mod_dependencies(tree).unwrap()

    return ModAboutXML(
        package_id,
        before,
        after,
        incompatible,
        author,
        name,
        supported_versions,
        dependencies,
    )


def read_mod(path: Path):
    about_xml_path = find_about_xml(path)
    if not about_xml_path:
        return Err(f"No About.xml found in {path}")
    test = parse_xml(about_xml_path)
    return test


if __name__ == "__main__":
    read_mod(Path("/games/rimworld-dev/game/Mods/jaxe.rimhud/"))
    print("success")
