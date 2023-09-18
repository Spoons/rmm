from rmm.mod import ModAboutXML
import pytest


@pytest.fixture()
def mod():
    return ModAboutXML(
        "package_id",
        ["before"],
        ["after"],
        ["incompatible"],
        "author",
        "name",
        ["supported_versions"],
        [],
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
    assert mod.incompatible == ["incompatible"]
    assert mod.author == "author"
    assert mod.name == "name"
    assert mod.supported_versions == ["supported_versions"]
