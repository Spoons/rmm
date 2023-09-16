import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Generator, List, Optional, Union, cast
from xml.dom import minidom


def platform() -> Optional[str]:
    return sys.platform


def execute(cmd) -> Generator[str, None, None]:
    with subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        text=True,
        close_fds=True,
        shell=True,
    ) as proc:
        for line in iter(proc.stdout.readline, b""):
            yield line
            if (r := proc.poll()) is not None:
                if r != 0:
                    raise subprocess.CalledProcessError(r, cmd)
                break


def run_sh(cmd: str) -> str:
    # Will raise a CalledProcessError if non-zero return code
    return subprocess.check_output(cmd, text=True, shell=True).strip()


def copy(source: Path, destination: Path, recursive: bool = False):
    if recursive:
        shutil.copytree(source, destination)
    else:
        shutil.copy2(source, destination, follow_symlinks=True)


def move(source: Path, destination: Path):
    shutil.move(source, destination)


def remove(dest: Path):
    shutil.rmtree(dest)


def list_set_intersection(a: list, b: list) -> list:
    return list(set(a) & set(b))


def list_loop_intersection(a: list, b: list) -> list:
    return [value for value in a if value in b]


def list_loop_exclusion(a: list, b: list) -> list:
    return [value for value in a if value not in b]


def list_grab(element: str, root: ET.Element) -> Optional[List[str]]:
    try:
        return cast(
            Optional[List[str]],
            [n.text for n in cast(ET.Element, root.find(element)).findall("li")],
        )
    except AttributeError:
        return None


def element_grab(element: str, root: ET.Element) -> Optional[str]:
    try:
        return cast(ET.Element, root.find(element)).text
    except AttributeError:
        return None


def et_pretty_xml(root: ET.Element) -> str:
    return minidom.parseString(
        re.sub(
            r"[\n\t\s]*",
            "",
            (ET.tostring(cast(ET.Element, root), "utf-8").decode()),
        )
    ).toprettyxml(indent="  ", newl="\n")


def sanitize_path(path: Union[str, Path]):
    if isinstance(path, Path):
        path = str(path)

    if platform() == "win32":
        path.replace('"', "")

    return Path(path).expanduser()
