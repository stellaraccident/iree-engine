# Copyright 2023 Stella Laurenzo
#
# Licensed under the Apache License v2.0 with LLVM Exceptions.
# See https://llvm.org/LICENSE.txt for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

# TODO: Upstream this to IREE.

from contextlib import closing
from pathlib import Path
from typing import Sequence, Optional, Union

from . import compiler_dl as dl

__all__ = ["Compiler"]


class Compiler:
    """Encapsulates a compiler session.

    A compiler session can be used to perform multiple invocations and
    has flags set that are local to the session. It shares some state
    between invocations for performance.
    """

    def __init__(self):
        self._session = dl.Session()

    def set_flags(self, *flags: Sequence[str]):
        self._session.set_flags(*flags)

    def get_flags(self) -> Sequence[str]:
        return self._session.get_flags()

    def load_buffer(self, buffer, *, buffer_name: Optional[str]) -> "Pipeline":
        """Opens a source backed by a buffer in memory."""
        source = dl.Source.wrap_buffer(self._session, buffer, buffer_name=buffer_name)
        return self._start_pipeline(source)

    def load_file(self, file_path: Union[str, Path]) -> "Pipeline":
        """Opens a source backed by a file."""
        source = dl.Source.open_file(self._session, str(file_path))
        return self._start_pipeline(source)

    def _start_pipeline(self, source: dl.Source) -> "Pipeline":
        inv = dl.Invocation(self._session)
        inv.enable_console_diagnostics()  # TODO: Real diagnostics
        # TODO: Crash handler, etc.
        if not inv.parse_source(source):
            # TODO: Capture diagnostics into exception.
            raise ValueError("Error parsing source (see diagnostics)")
        return Pipeline(self, inv)

    def open_output_file(self, file_path: Union[str, Path]) -> dl.Output:
        return dl.Output.open_file(str(file_path))

    def open_output_membuffer(self) -> dl.Output:
        return dl.Output.open_membuffer()


class Pipeline:
    """Encapsulates a compilation pipeline in progress."""

    def __init__(self, compiler: Compiler, inv: dl.Invocation):
        self._compiler = compiler
        self._inv = inv

    def __del__(self):
        self.close()

    def close(self):
        if self._inv:
            self._inv.close()
            self._inv = None

    def execute(
        self,
        pipeline_type: dl.PipelineType = dl.PipelineType.IREE_COMPILER_PIPELINE_STD,
    ):
        if not self._inv.execute(pipeline_type):
            # TODO: Capture diagnostics into exception.
            raise ValueError("Error parsing source (see diagnostics)")

    def output_ir(self, output: dl.Output):
        self._inv.output_ir(output)

    def output_vm_bytecode(self, output: dl.Output):
        self._inv.output_vm_bytecode(output)
