# Copyright 2023 Stella Laurenzo
#
# Licensed under the Apache License v2.0 with LLVM Exceptions.
# See https://llvm.org/LICENSE.txt for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception


from . import compiler_dl as dl

from threading import Lock

__all__ = ["Compiler"]


class Compiler:
    """Encapsulates a compiler session.

    A compiler session can be used to perform multiple invocations and
    has flags set that are local to the session. It shares some state
    between invocations for performance.
    """

    def __init__(self):
        self._lock = Lock()
        self._session = dl.Session()

    def open_source_buffer(self, buffer):
        """Opens a source backed by a buffer in memory."""
        ...
