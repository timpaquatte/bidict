import pytest_mutagen as mg
# from .test_properties import *

from bidict._mut import MutableBidict
from bidict._base import BidictBase
from bidict._orderedbase import OrderedBidictBase
from bidict._orderedbidict import OrderedBidict
from bidict._exc import KeyDuplicationError

mg.link_to_file("test_properties.py")


@mg.mutant_of("MutableBidict.pop", "POP_NOTHING")
def pop_nothing(self, key, default=0):
    pass

@mg.mutant_of("MutableBidict.popitem", "POP_NOTHING")
def popitem_nothing(self):
    pass

@mg.mutant_of("OrderedBidictBase._pop", "POP_NOTHING")
def _pop_nothing(self, key):    
    pass

@mg.mutant_of("MutableBidict.__setitem__", "__SETITEM__NOTHING")
def __setitem__nothing(self, key):
    pass

from bidict._dup import ON_DUP_RAISE
@mg.mutant_of("MutableBidict.put", "PUT_NOTHING")
def put_nothing(self, key, val, on_dup=ON_DUP_RAISE):
    pass

@mg.mutant_of("MutableBidict.putall", "PUT_NOTHING")
def putall_nothing(self, items, on_dup=ON_DUP_RAISE):
    pass

@mg.mutant_of("MutableBidict.clear", "CLEAR_NOTHING")
def mutable_clear_nothing(self):
    pass

@mg.mutant_of("OrderedBidict.clear", "CLEAR_NOTHING")
def ordered_clear_nothing(self):
    pass

@mg.mutant_of("MutableBidict.update", "UPDATE_NOTHING")
def update_nothing(self, *args, **kw):
    pass

@mg.mutant_of("MutableBidict.__delitem__", "__DELITEM__NOTHING")
def __delitem__nothing(self, key):
    if self.__getitem__(key):
        return
    raise KeyError