from rmm.Mod import Mod
import pytest


@pytest.fixture()
def mod():
    return Mod(
        "package_id", ["before"], ["after"], "author", "name", ["supported_versions"]
    )


def test_mod_display_name(mod):
    assert mod.display_name() == "name"


def test_mod_eq(mod):
    assert mod == mod


def test_mod_hash(mod):
    assert hash(mod) == hash(mod)


def test_mod_required(mod):
    assert mod.package_id == "package_id"
    assert mod.before == ["before"]
    assert mod.after == ["after"]
    assert mod.author == "author"
    assert mod.name == "name"
    assert mod.supported_versions == ["supported_versions"]
