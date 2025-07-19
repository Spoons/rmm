import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Generator, Optional, Union, cast
from xml.dom import minidom


def platform() -> str:
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


def extract_download_path() -> str:
    """
    Get the path on where steamcmd downloads items from the query function
    """
    output: str = run_sh(
        'env HOME="/tmp/rmm-dltest" steamcmd +login anonymous +workshop_download_item 294100 3128152016 +quit'
    )
    regex = re.compile(r'".*rmm-dltest\/([\w\/-]+294100).*"')
    match = regex.search(output).group(1)
    return match
