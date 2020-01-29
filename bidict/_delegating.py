# -*- coding: utf-8 -*-
# Copyright 2009-2020 Joshua Bronson. All Rights Reserved.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


"""Provide :class:`_DelegatingMixin`."""

from typing import Iterator, KeysView, ItemsView, cast

from ._abc import KT, VT
from ._base import BidictBase


class _DelegatingMixin:
    """Provide optimized implementations of several methods by delegating to backing dicts.

    Used to override less efficient implementations inherited by :class:`~collections.abc.Mapping`.
    """

    __slots__ = ()

    def __iter__(self: BidictBase[KT, VT]) -> Iterator[KT]:
        """Iterator over the contained keys."""
        return iter(self._fwdm)

    def keys(self: BidictBase[KT, VT]) -> KeysView[KT]:
        """A set-like object providing a view on the contained keys."""
        return cast(KeysView[KT], self._fwdm.keys())

    def values(self: BidictBase[KT, VT]) -> KeysView[VT]:
        """A set-like object providing a view on the contained values."""
        return cast(KeysView[VT], self._invm.keys())

    def items(self: BidictBase[KT, VT]) -> ItemsView[KT, VT]:
        """A set-like object providing a view on the contained items."""
        return cast(ItemsView[KT, VT], self._fwdm.items())
