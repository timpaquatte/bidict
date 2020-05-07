import pytest_mutagen as mg
# from .test_properties import *

from bidict._orderedbase import OrderedBidictBase

mg.link_to_file("test_properties.py")


@mg.mutant_of("OrderedBidictBase.__iter__", "ITER_LIKE_UNORDERED")
def __iter__mut(self):
    return iter(self._fwdm)

@mg.mutant_of("OrderedBidictBase._pop", "POP_MUT")
def _pop_mut(self, key):
    nodefwd = self._fwdm.pop(key)
    val = self._invm.inverse.pop(nodefwd)  # pylint: disable=no-member
    return val

@mg.mutant_of("OrderedBidictBase._already_have", "ALREADY_HAVE_TRUE", description="_already_have always returns true")
def _already_have_true(key, val, oldkey, oldval):
    return True

@mg.mutant_of("OrderedBidictBase._already_have", "ALREADY_HAVE_FALSE", description="_already_have always returns false")
def _already_have_false(key, val, oldkey, oldval):
    return False

@mg.mutant_of("OrderedBidictBase.equals_order_sensitive", "EQUALS_ORDER_UNSENSITIVE")
def equals_order_sensitive_mut(self, other):
    return self == other