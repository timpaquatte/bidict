# -*- coding: utf-8 -*-
# Copyright 2009-2020 Joshua Bronson. All Rights Reserved.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


"""Provides :class:`OnDup` and related functionality."""


from enum import Enum
from typing import NamedTuple


class OnDupAction(Enum):
    """An action to take to prevent duplication from occurring."""

    #: Raise a :class:`~bidict.DuplicationError`.
    RAISE = 'RAISE'
    #: Overwrite existing items with new items.
    DROP_OLD = 'DROP_OLD'
    #: Keep existing items and drop new items.
    DROP_NEW = 'DROP_NEW'

    def __repr__(self):
        return f'<bidict.{self.name}>'  # pragma: no cover


RAISE = OnDupAction.RAISE
DROP_OLD = OnDupAction.DROP_OLD
DROP_NEW = OnDupAction.DROP_NEW


# TODO: document that implicit (kv=kv or val) support was dropped
class OnDup(NamedTuple):
    r"""Three :class:`OnDupAction`\s specifying how to handle the three kinds of duplication.

    *See also* :ref:`basic-usage:Values Must Be Unique`
    """

    key: OnDupAction = DROP_OLD
    val: OnDupAction = RAISE
    kv: OnDupAction = RAISE


#: Default :class:`OnDup` used for the
#: :meth:`~bidict.bidict.__init__`,
#: :meth:`~bidict.bidict.__setitem__`, and
#: :meth:`~bidict.bidict.update` methods.
ON_DUP_DEFAULT = OnDup()
#: An :class:`OnDup` whose members are all :obj:`RAISE`.
ON_DUP_RAISE = OnDup(key=RAISE, val=RAISE, kv=RAISE)
#: An :class:`OnDup` whose members are all :obj:`DROP_OLD`.
ON_DUP_DROP_OLD = OnDup(key=DROP_OLD, val=DROP_OLD, kv=DROP_OLD)
