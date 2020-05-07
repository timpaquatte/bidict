import pytest_mutagen as mg
# from .test_properties import *

from bidict._base import BidictBase
from bidict._sntl import _MISS, _NOOP

mg.link_to_file("test_properties.py")

@mg.mutant_of("BidictBase.copy", "COPY_INVERTED")
def copy_inverted(self):
    cp = self.__class__.__new__(self.__class__)  # pylint: disable=invalid-name
    cp._fwdm = self._invm.copy()  # pylint: disable=protected-access
    cp._invm = self._fwdm.copy()  # pylint: disable=protected-access
    cp._init_inv()  # pylint: disable=protected-access
    return cp

@mg.mutant_of("BidictBase._update", "BASE_UPDATE_NOTHING")
def _update_nothing(self, *args, **kw):  # pylint: disable=arguments-differ
    pass

@mg.mutant_of("BidictBase._dedup_item", "DEDUP_ITEM_NOOP")
def _dedup_item(self, key, val, on_dup):  # pylint: disable=too-many-branches
    return _NOOP

@mg.mutant_of("BidictBase._undo_write", "UNDO_WRITE_NOTHING")
def _undo_write_nothing(self, dedup_result, write_result):
    return

@mg.mutant_of("BidictBase._undo_write", "UNDO_WRITE_IS_POP")
def _undo_write_is_pop(self, dedup_result, write_result):
    key, val, oldkey, oldval = write_result
    self._pop(key)

@mg.mutant_of("BidictBase._put", "PUT_ALWAYS_0")
def _put(self, key, val, on_dup):
    dedup_result = self._dedup_item(key, val, on_dup)
    if dedup_result is not _NOOP:
        self._write_item(key, 0, dedup_result)

@mg.mutant_of("BidictBase.__eq__", "EQ_TRUE")
def __eq__true(self, other):
    return True

@mg.mutant_of("BidictBase.__eq__", "EQ_FALSE")
def __eq__false(self, other):
    return False

@mg.mutant_of("BidictBase.inverse", "INV_MUT", description="inverse does not check if self._inv is not None")
def inverse_mut(self):
    return self._inv

@mg.mutant_of("BidictBase._pop", "POP_MUT", description="pop does not delete the key")
def _pop_mut(self, key):
    val = self._fwdm.pop(key)
    return val

@mg.mutant_of("BidictBase._already_have", "ALREADY_HAVE_FALSE", description="_already_have always returns false")
def _already_have_false(key, val, oldkey, oldval):
    return False

@mg.mutant_of("BidictBase._put", "PUT_NOTHING", description="put does not do anything")
def _put_mut(self, key, val, on_dup):
    return

@mg.mutant_of("BidictBase.__len__", "LEN_0")
def __len__mut(self):
    return 0

@mg.mutant_of("BidictBase._already_have", "ALREADY_HAVE_TRUE", description="_already_have always returns true")
def _already_have_true(key, val, oldkey, oldval):
    return True

@mg.mutant_of("BidictBase._isinv", "IS_INV_INVERTED")
def _is_inv_inverted(self):
    return not self._inv is None
