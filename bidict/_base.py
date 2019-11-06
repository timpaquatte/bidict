# -*- coding: utf-8 -*-
# Copyright 2009-2020 Joshua Bronson. All Rights Reserved.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


#==============================================================================
#                    * Welcome to the bidict source code *
#==============================================================================

# Doing a code review? You'll find a "Code review nav" comment like the one
# below at the top and bottom of the most important source files. This provides
# a suggested initial path through the source when reviewing.
#
# Note: If you aren't reading this on https://github.com/jab/bidict, you may be
# viewing an outdated version of the code. Please head to GitHub to review the
# latest version, which contains important improvements over older versions.
#
# Thank you for reading and for any feedback you provide.

#                             * Code review nav *
#==============================================================================
# ← Prev: _abc.py             Current: _base.py   Next:     _frozenbidict.py →
#==============================================================================


"""Provides :class:`BidictBase`."""

from functools import wraps
from typing import (
    AbstractSet, Any, Callable, Dict, Generic, Iterator, List, Mapping, Optional, Type, TypeVar,
    Tuple, Union,
)
from warnings import warn
from weakref import ref

from ._abc import BidirectionalMapping
from ._dup import ON_DUP_DEFAULT, RAISE, DROP_OLD, DROP_NEW, OnDup
from ._exc import (
    DuplicationError, KeyDuplicationError, ValueDuplicationError, KeyAndValueDuplicationError)
from ._sntl import _Sentinel, _MISS, _NOOP
from ._util import _iteritems_args_kw

KT = TypeVar('KT')
VT = TypeVar('VT')


class _BaseResult(Generic[KT, VT]):
    __slots__ = ('isdupkey', 'isdupval', 'invbyval', 'fwdbykey')

    def __init__(self, isdupkey: bool, isdupval: bool, invbyval: KT, fwdbykey: VT):
        self.isdupkey = isdupkey
        self.isdupval = isdupval
        self.invbyval = invbyval
        self.fwdbykey = fwdbykey

    def __iter__(self) -> Iterator[Union[bool, KT, VT]]:
        return iter(self.as_tuple())

    def __getitem__(self, index: Union[int, slice]) -> Union[bool, KT, VT, Tuple[Union[bool, KT, VT]]]:
        return self.as_tuple()[index]

    def as_tuple(self) -> Tuple[bool, bool, KT, VT]:
        return (self.isdupkey, self.isdupval, self.invbyval, self.fwdbykey)


class _DedupResult(_BaseResult[KT, VT]):
    pass


class _FailedResult(_BaseResult[Any, Any]):  # TODO: temporarily changed from [_Marker, _Marker] during merge
    pass


class _WriteResult(Generic[KT, VT]):
    __slots__ = ('key', 'val', 'oldkey', 'oldval')

    def __init__(self, key: KT, val: VT, oldkey: KT, oldval: VT):
        self.key = key
        self.val = val
        self.oldkey = oldkey
        self.oldval = oldval

    def __iter__(self) -> Iterator[Union[KT, VT]]:
        return iter(self.as_tuple())

    def __getitem__(self, index: Union[int, slice]) -> Union[KT, VT, Tuple[Union[KT, VT]]]:
        return self.as_tuple()[index]

    def as_tuple(self) -> Tuple[KT, VT, KT, VT]:
        return (self.key, self.val, self.oldkey, self.oldval)


_NODUP = _FailedResult(False, False, _MISS, _MISS)


# TODO: Remove this compatibility decorator in a future release. pylint: disable=fixme
def _on_dup_compat(__init__):
    deprecated = ('on_dup_key', 'on_dup_val', 'on_dup_kv')
    msg = 'The `on_dup_key`, `on_dup_val`, and `on_dup_kv` class attrs are deprecated and ' \
          'will be removed in a future version of bidict. Use the `on_dup` class attr instead.'

    @wraps(__init__)
    def wrapper(self, *args, **kw):
        cls = self.__class__
        shim = {s[len('on_dup_'):]: getattr(cls, s) for s in deprecated if hasattr(cls, s)}
        if shim:
            warn(msg, stacklevel=2)
            cls.on_dup = OnDup(**shim)
        return __init__(self, *args, **kw)

    return wrapper


# Since BidirectionalMapping implements __subclasshook__, and BidictBase
# provides all the required attributes that the __subclasshook__ checks for,
# BidictBase would be a (virtual) subclass of BidirectionalMapping even if
# it didn't subclass it explicitly. But subclassing BidirectionalMapping
# explicitly allows BidictBase to inherit any useful implementations that
# BidirectionalMapping provides that aren't part of the required interface,
# such as its implementations of `__inverted__` and `values`.

class BidictBase(BidirectionalMapping[KT, VT]):
    """Base class implementing :class:`BidirectionalMapping`."""

    __slots__ = ('_fwdm', '_invm', '_inv', '_invweak', '_hash', '__weakref__')

    #: The default :class:`~bidict.OnDup`
    #: (in effect during e.g. :meth:`~bidict.bidict.__init__` calls)
    #: that governs behavior when a provided item
    #: duplicates the key or value of other item(s).
    #:
    #: *See also* :ref:`basic-usage:Values Must Be Unique`, :doc:`extending`
    on_dup = ON_DUP_DEFAULT

    _fwdm_cls = dict  # type: Type[Dict[KT, VT]]  # needs Dict, since we require .copy()
    _invm_cls = dict  # type: Type[Dict[VT, KT]]  # needs Dict, since we require .copy()

    #: The object used by :meth:`__repr__` for printing the contained items.
    _repr_delegate = dict  # type: Type[Dict[KT, VT]]

    _inv_cls_ = None  # type: Optional[Type[BidictBase[VT, KT]]]

    @_on_dup_compat
    def __init__(self, *args, **kw):  # pylint: disable=super-init-not-called
        # type: (*Tuple[KT, VT], **Dict[KT, VT]) -> None
        """Make a new bidirectional dictionary.
        The signature behaves like that of :class:`dict`.
        Items passed in are added in the order they are passed,
        respecting the :attr:`on_dup` class attribute in the process.
        """
        self._inv = None  # type: Optional[BidictBase[VT, KT]]
        #: The backing :class:`~collections.abc.Mapping`
        #: storing the forward mapping data (*key* → *value*).
        self._fwdm = self._fwdm_cls()  # type: Dict[KT, VT]
        #: The backing :class:`~collections.abc.Mapping`
        #: storing the inverse mapping data (*value* → *key*).
        self._invm = self._invm_cls()  # type: Dict[VT, KT]
        self._init_inv()  # lgtm [py/init-calls-subclass]
        if args or kw:
            self._update(True, self.on_dup, *args, **kw)

    def _init_inv(self):
        # Compute the type for this bidict's inverse bidict (will be different from this
        # bidict's type if _fwdm_cls and _invm_cls are different).
        inv_cls = self._inv_cls()
        # Create the inverse bidict instance via __new__, bypassing its __init__ so that its
        # _fwdm and _invm can be assigned to this bidict's _invm and _fwdm. Store it in self._inv,
        # which holds a strong reference to a bidict's inverse, if one is available.
        self._inv = inv = inv_cls.__new__(inv_cls)
        inv._fwdm = self._invm  # pylint: disable=protected-access
        inv._invm = self._fwdm  # pylint: disable=protected-access
        # Only give the inverse a weak reference to this bidict to avoid creating a reference cycle,
        # stored in the _invweak attribute. See also the docs in
        # :ref:`addendum:Bidict Avoids Reference Cycles`
        inv._inv = None  # pylint: disable=protected-access
        inv._invweak = ref(self)  # pylint: disable=protected-access
        # Since this bidict has a strong reference to its inverse already, set its _invweak to None.
        self._invweak = None

    @classmethod
    def _inv_cls(cls: 'Type[BidictBase[KT, VT]]') -> 'Type[BidictBase[VT, KT]]':
        """The inverse of this bidict type, i.e. one with *_fwdm_cls* and *_invm_cls* swapped."""
        if cls._fwdm_cls is cls._invm_cls:
            return cls  # type: ignore
        if cls._inv_cls_:
            return cls._inv_cls_

        class _Inv(cls):  # type: ignore
            _fwdm_cls = cls._invm_cls
            _invm_cls = cls._fwdm_cls
            _inv_cls_ = cls
        _Inv.__name__ = cls.__name__ + 'Inv'
        cls._inv_cls_ = _Inv
        return cls._inv_cls_

    @property
    def _isinv(self) -> bool:
        return self._inv is None

    @property
    def inverse(self) -> 'BidictBase[VT, KT]':
        """The inverse of this bidict.

        *See also* :attr:`inv`
        """
        # Resolve and return a strong reference to the inverse bidict.
        # One may be stored in self._inv already.
        if self._inv is not None:
            return self._inv
        # Otherwise a weakref is stored in self._invweak. Try to get a strong ref from it.
        inv = self._invweak()  # type: Optional[BidictBase[VT, KT]]  # pylint: disable=not-callable
        if inv is not None:
            return inv
        # Refcount of referent must have dropped to zero, as in `bidict().inv.inv`. Init a new one.
        self._init_inv()  # Now this bidict will retain a strong ref to its inverse.
        assert self._inv is not None, 'call to _init_inv failed to initialize _inv'
        return self._inv

    @property
    def inv(self):
        """Alias for :attr:`inverse`."""
        return self.inverse

    def __getstate__(self) -> Dict[str, Any]:
        """Needed to enable pickling due to use of :attr:`__slots__` and weakrefs.

        *See also* :meth:`object.__getstate__`
        """
        state = {}
        for cls in self.__class__.__mro__:
            slots = getattr(cls, '__slots__', ())  # type: Tuple[str]
            for slot in slots:
                if hasattr(self, slot):
                    state[slot] = getattr(self, slot)
        # weakrefs can't be pickled.
        state.pop('_invweak', None)  # Added back in __setstate__ via _init_inv call.
        state.pop('__weakref__', None)  # Not added back in __setstate__. Python manages this one.
        return state

    def __setstate__(self, state: Dict[str, Any]):
        """Implemented because use of :attr:`__slots__` would prevent unpickling otherwise.

        *See also* :meth:`object.__setstate__`
        """
        for slot, value in state.items():
            setattr(self, slot, value)
        self._init_inv()

    def __repr__(self) -> str:
        """See :func:`repr`."""
        clsname = self.__class__.__name__
        if not self:
            return '%s()' % clsname
        return '%s(%r)' % (clsname, self._repr_delegate(self.items()))

    # The inherited Mapping.__eq__ implementation would work, but it's implemented in terms of an
    # inefficient ``dict(self.items()) == dict(other.items())`` comparison, so override it with a
    # more efficient implementation.
    def __eq__(self, other: Any) -> bool:
        """*x.__eq__(other)　⟺　x == other*

        Equivalent to *dict(x.items()) == dict(other.items())*
        but more efficient.

        Note that :meth:`bidict's __eq__() <bidict.bidict.__eq__>` implementation
        is inherited by subclasses,
        in particular by the ordered bidict subclasses,
        so even with ordered bidicts,
        :ref:`== comparison is order-insensitive <eq-order-insensitive>`.

        *See also* :meth:`bidict.FrozenOrderedBidict.equals_order_sensitive`
        """
        if not isinstance(other, Mapping) or len(self) != len(other):
            return False
        selfget = self.get  # type: Callable[[KT, _Sentinel], Union[VT, _Sentinel]]
        return all(selfget(k, _MISS) == v for (k, v) in other.items())

    # The following methods are mutating and so are not public. But they are implemented in this
    # non-mutable base class (rather than the mutable `bidict` subclass) because they are used here
    # during initialization (starting with the `_update` method). (Why is this? Because `__init__`
    # and `update` share a lot of the same behavior (inserting the provided items while respecting
    # `on_dup`), so it makes sense for them to share implementation too.)
    def _pop(self, key: KT) -> VT:
        val = self._fwdm.pop(key)
        del self._invm[val]
        return val

    def _put(self, key: KT, val: VT, on_dup: OnDup):
        dedup_result = self._dedup_item(key, val, on_dup)
        if isinstance(dedup_result, _DedupResult):
            self._write_item(key, val, dedup_result)

    def _dedup_item(self, key: KT, val: VT, on_dup: OnDup) -> Union[_DedupResult, _Sentinel]:  # pylint: disable=too-many-branches
        """
        Check *key* and *val* for any duplication in self.

        Handle any duplication as per the passed in *on_dup*.

        (key, val) already present is construed as a no-op, not a duplication.

        If duplication is found and the corresponding :class:`~bidict.OnDupAction` is
        :attr:`RAISE`, raise the appropriate error.

        If duplication is found and the corresponding :class:`~bidict.OnDupAction` is
        :attr:`DROP_NEW`, return *None*.

        If duplication is found and the corresponding :class:`~bidict.OnDupAction` is
        :attr:`DROP_OLD`,
        or if no duplication is found,
        return the _DedupResult *(isdupkey, isdupval, oldkey, oldval)*.
        """
        fwdm = self._fwdm
        invm = self._invm
        oldval = fwdm.get(key, _MISS)  # type: Union[VT, _Sentinel]
        oldkey = invm.get(val, _MISS)  # type: Union[KT, _Sentinel]
        isdupkey = oldval is not _MISS
        isdupval = oldkey is not _MISS
        dedup_result = _DedupResult(isdupkey, isdupval, oldkey, oldval)
        if not isinstance(oldval, _Marker) and not isinstance(oldkey, _Marker):
            if self._already_have(key, val, oldkey, oldval):
                # (key, val) duplicates an existing item -> no-op.
                return _NOOP
            # key and val each duplicate a different existing item.
            if on_dup.kv is RAISE:
                raise KeyAndValueDuplicationError(key, val)
            if on_dup.kv is DROP_NEW:
                return _NOOP
            if on_dup.kv is not DROP_OLD:  # pragma: no cover
                raise ValueError(on_dup.kv)
            # Fall through to the return statement on the last line.
        elif isdupkey:
            if on_dup.key is RAISE:
                raise KeyDuplicationError(key)
            if on_dup.key is DROP_NEW:
                return _NOOP
            if on_dup.key is not DROP_OLD:  # pragma: no cover
                raise ValueError(on_dup.key)
            # Fall through to the return statement on the last line.
        elif isdupval:
            if on_dup.val is RAISE:
                raise ValueDuplicationError(val)
            if on_dup.val is DROP_NEW:
                return _NOOP
            if on_dup.val is not DROP_OLD:  # pragma: no cover
                raise ValueError(on_dup.val)
            # Fall through to the return statement on the last line.
        # else neither isdupkey nor isdupval.
        return dedup_result

    @staticmethod
    def _already_have(key: KT, val: VT, oldkey: KT, oldval: VT) -> bool:
        # Overridden by _orderedbase.OrderedBidictBase.
        isdup = oldkey == key
        assert isdup == (oldval == val), '%r %r %r %r' % (key, val, oldkey, oldval)
        return isdup

    def _write_item(self, key: KT, val: VT, dedup_result: _BaseResult) -> _WriteResult[KT, VT]:
        isdupkey, isdupval, oldkey, oldval = dedup_result.as_tuple()
        fwdm = self._fwdm
        invm = self._invm
        fwdm[key] = val
        invm[val] = key
        if isdupkey:
            del invm[oldval]
        if isdupval:
            del fwdm[oldkey]
        return _WriteResult(key, val, oldkey, oldval)

    def _update(self, init, on_dup, *args, **kw):
        # args[0] may be a generator that yields many items, so process input in a single pass.
        if not args and not kw:
            return
        can_skip_dup_check = not self and not kw and isinstance(args[0], BidirectionalMapping)
        if can_skip_dup_check:
            self._update_no_dup_check(args[0])
            return
        can_skip_rollback = init or RAISE not in on_dup
        if can_skip_rollback:
            self._update_no_rollback(on_dup, *args, **kw)
        else:
            self._update_with_rollback(on_dup, *args, **kw)

    def _update_no_dup_check(self, other: Mapping[KT, VT], _nodup: _BaseResult = _NODUP):
        write_item = self._write_item
        for (key, val) in other.items():
            write_item(key, val, _nodup)

    def _update_no_rollback(self, on_dup: OnDup, *args, **kw):
        put = self._put
        for (key, val) in _iteritems_args_kw(*args, **kw):
            put(key, val, on_dup)

    def _update_with_rollback(self, on_dup: OnDup, *args, **kw):
        """Update, rolling back on failure."""
        writelog = []  # type: List[Tuple[_DedupResult, _WriteResult]]
        appendlog = writelog.append
        dedup_item = self._dedup_item
        write_item = self._write_item
        for (key, val) in _iteritems_args_kw(*args, **kw):
            try:
                dedup_result = dedup_item(key, val, on_dup)
            except DuplicationError:
                undo_write = self._undo_write
                for dedup_result, write_result in reversed(writelog):
                    undo_write(dedup_result, write_result)
                raise
            if isinstance(dedup_result, _DedupResult):
                write_result = write_item(key, val, dedup_result)
                appendlog((dedup_result, write_result))

    # : _WriteResult[KT, VT]):
    def _undo_write(self, dedup_result: _DedupResult, write_result: _WriteResult[KT, VT]):
        isdupkey, isdupval, _, _ = dedup_result.as_tuple()
        key, val, oldkey, oldval = write_result.as_tuple()
        if not isdupkey and not isdupval:
            self._pop(key)
            return
        fwdm = self._fwdm
        invm = self._invm
        if isdupkey:
            fwdm[key] = oldval
            invm[oldval] = key
            if not isdupval:
                del invm[val]
        if isdupval:
            invm[val] = oldkey
            fwdm[oldkey] = val
            if not isdupkey:
                del fwdm[key]

    def copy(self) -> 'BidictBase[KT, VT]':
        """A shallow copy."""
        # Could just ``return self.__class__(self)`` here instead, but the below is faster. It uses
        # __new__ to create a copy instance while bypassing its __init__, which would result
        # in copying this bidict's items into the copy instance one at a time. Instead, make whole
        # copies of each of the backing mappings, and make them the backing mappings of the copy,
        # avoiding copying items one at a time.
        copy = self.__class__.__new__(self.__class__)  # type: BidictBase[KT, VT]
        copy._fwdm = self._fwdm.copy()  # pylint: disable=protected-access
        copy._invm = self._invm.copy()  # pylint: disable=protected-access
        copy._init_inv()  # pylint: disable=protected-access
        return copy

    def __copy__(self) -> 'BidictBase[KT, VT]':
        """Used for the copy protocol.

        *See also* the :mod:`copy` module
        """
        return self.copy()

    def __len__(self) -> int:
        """The number of contained items."""
        return len(self._fwdm)

    def __iter__(self) -> Iterator[KT]:  # lgtm [py/inheritance/incorrect-overridden-signature]
        """Iterator over the contained items."""
        # No default implementation for __iter__ inherited from Mapping ->
        # always delegate to _fwdm.
        return iter(self._fwdm)

    def __getitem__(self, key: KT) -> VT:
        """*x.__getitem__(key)　⟺　x[key]*"""
        return self._fwdm[key]

    def values(self) -> AbstractSet[VT]:  # type: ignore
        """A set-like object providing a view on the contained values.

        Note that because the values of a :class:`~bidict.BidirectionalMapping`
        are the keys of its inverse,
        this returns a :class:`~collections.abc.KeysView`
        rather than a :class:`~collections.abc.ValuesView`,
        which has the advantages of constant-time containment checks
        and supporting set operations.
        """
        return self.inverse.keys()


#                             * Code review nav *
#==============================================================================
# ← Prev: _abc.py             Current: _base.py   Next:     _frozenbidict.py →
#==============================================================================
