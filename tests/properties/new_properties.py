from . import _strategies as st
from hypothesis import given, assume

from bidict._dup import ON_DUP_DROP_OLD
from bidict import namedbidict


def test_isinv_correct():
    ElementMap = namedbidict("ElementMap", "symbol", "name")
    noble_gases = ElementMap()
    noble_gases["He"] = "helium"

    assert noble_gases.name_for['He'] == "helium"
    assert noble_gases.symbol_for['helium'] == "He"

@given(st.MUTABLE_BIDICTS, st.PAIRS)
def test_put_correct(mb, pair):
    key, val = pair
    copy = mb.copy()
    mb.put(key, val, ON_DUP_DROP_OLD)
    if (key, val) in copy.items():
        assert copy == mb
    else:
        assert copy != mb

@given(st.MUTABLE_BIDICTS)
def test_clear_correct(mb):
    mb.clear()
    assert len(mb.items()) == 0

@given(st.MUTABLE_BIDICTS, st.PAIRS)
def test_update_correct(mb, pair):
    key, value = pair
    assume(key not in mb.keys())
    assume(value not in mb.values())

    mb.update([pair])
    assert mb[key] == value

@given(st.MUTABLE_BIDICTS)
def test_del_correct(mb):
    assume(len(mb.items()) > 0)
    from random import choice
    rand_key = choice(list(mb.keys()))

    del mb[rand_key]
    assert not rand_key in mb
