import pytest

from rmm.error import Ok, Err, Result


def test_ok_error():
    assert Ok(1).is_error() == False


def test_err_error():
    assert Err(1).is_error() == True


def test_ok_unwrap():
    assert Ok(1).unwrap() == 1


def test_err_unwrap():
    with pytest.raises(TypeError):
        Err(1).unwrap()


def test_ok_unwrap_or():
    assert Ok(1).unwrap_or(2) == 1


def test_err_unwrap_or():
    assert Err(1).unwrap_or(2) == 2
