# Copyright 2023 Stella Laurenzo
#
# Licensed under the Apache License v2.0 with LLVM Exceptions.
# See https://llvm.org/LICENSE.txt for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""Dynamic library binding to libIREECompiler.so, using ctypes."""

# TODO: Upstream this to IREE.

from ctypes import *
from enum import IntEnum
from pathlib import Path
from typing import List, Optional, Sequence

import ctypes
import logging
import os
import platform

__all__ = [
    "Invocation",
    "Output",
    "Session",
    "Source",
]

_dylib = None

_GET_FLAG_CALLBACK = CFUNCTYPE(None, c_void_p, c_size_t, c_void_p)


def _setsig(f, restype, argtypes):
    f.restype = restype
    f.argtypes = argtypes


def _init_dylib():
    global _dylib
    if _dylib:
        return
    dylib_path = _probe_iree_compiler_dylib()
    if dylib_path is None:
        # TODO: Look for a bundled dylib.
        raise RuntimeError("Could not find libIREECompiler.so")
    _dylib = cdll.LoadLibrary(dylib_path)

    # Setup signatures.
    # Error
    _setsig(_dylib.ireeCompilerErrorDestroy, None, [c_void_p])
    _setsig(_dylib.ireeCompilerErrorGetMessage, c_char_p, [c_void_p])

    # Invocation
    _setsig(_dylib.ireeCompilerInvocationCreate, c_void_p, [c_void_p])
    _setsig(_dylib.ireeCompilerInvocationDestroy, None, [c_void_p])
    _setsig(_dylib.ireeCompilerInvocationEnableConsoleDiagnostics, None, [c_void_p])
    _setsig(_dylib.ireeCompilerInvocationParseSource, c_bool, [c_void_p, c_void_p])
    _setsig(_dylib.ireeCompilerInvocationPipeline, c_bool, [c_void_p, c_int])
    _setsig(_dylib.ireeCompilerInvocationOutputIR, c_void_p, [c_void_p, c_void_p])
    _setsig(
        _dylib.ireeCompilerInvocationOutputVMBytecode, c_void_p, [c_void_p, c_void_p]
    )

    # Output
    _setsig(_dylib.ireeCompilerOutputDestroy, None, [c_void_p])
    _setsig(_dylib.ireeCompilerOutputOpenFile, c_void_p, [c_char_p, c_void_p])
    _setsig(_dylib.ireeCompilerOutputOpenMembuffer, c_void_p, [c_void_p])
    _setsig(_dylib.ireeCompilerOutputKeep, None, [c_void_p])
    _setsig(
        _dylib.ireeCompilerOutputWrite, c_void_p, [c_void_p, POINTER(c_char), c_size_t]
    )
    _setsig(
        _dylib.ireeCompilerOutputMapMemory,
        c_void_p,
        [c_void_p, c_void_p, POINTER(c_uint64)],
    )

    # Session
    _setsig(_dylib.ireeCompilerSessionCreate, c_void_p, [])
    _setsig(_dylib.ireeCompilerSessionDestroy, None, [c_void_p])
    _setsig(
        _dylib.ireeCompilerSessionGetFlags,
        None,
        [c_void_p, c_bool, c_void_p, c_void_p],
    )
    _setsig(
        _dylib.ireeCompilerSessionSetFlags,
        c_void_p,
        [c_void_p, c_int, c_void_p],
    )
    # Source
    _setsig(_dylib.ireeCompilerSourceDestroy, None, [c_void_p])
    _setsig(
        _dylib.ireeCompilerSourceOpenFile,
        c_void_p,
        [
            c_void_p,  # session
            c_char_p,  # filePath
            c_void_p,  # out_source
        ],
    )
    _setsig(
        _dylib.ireeCompilerSourceWrapBuffer,
        c_void_p,
        [
            c_void_p,  # session
            c_char_p,  # bufferName
            POINTER(c_char),  # buffer
            c_size_t,  # length
            c_bool,  # isNullTerminated
            c_void_p,  # out_source
        ],
    )


def _handle_error(err_p, exc_type=ValueError):
    if err_p is None:
        return
    message = _dylib.ireeCompilerErrorGetMessage(err_p).decode("UTF-8")
    _dylib.ireeCompilerErrorDestroy(err_p)
    raise exc_type(message)


class Session:
    def __init__(self):
        self._global_init = _global_init
        self._session_p = _dylib.ireeCompilerSessionCreate()

    def __del__(self):
        _dylib.ireeCompilerSessionDestroy(self._session_p)

    def invocation(self):
        return Invocation(self)

    def get_flags(self, non_default_only: bool = False) -> Sequence[str]:
        results = []

        @_GET_FLAG_CALLBACK
        def callback(flag_pointer, length, user_data):
            flag_bytes = string_at(flag_pointer, length)
            flag_value = flag_bytes.decode("UTF-8")
            results.append(flag_value)

        _dylib.ireeCompilerSessionGetFlags(
            self._session_p, non_default_only, callback, c_void_p(0)
        )
        return results

    def set_flags(self, *flags: Sequence[str]):
        argv_type = c_char_p * len(flags)
        argv = argv_type(*[flag.encode("UTF-8") for flag in flags])
        _handle_error(
            _dylib.ireeCompilerSessionSetFlags(self._session_p, len(argv), argv)
        )


class Output:
    """Wraps an iree_compiler_output_t."""

    def __init__(self, output_p: c_void_p):
        self._output_p = output_p
        self._local_dylib = _dylib

    def __del__(self):
        self.close()

    def close(self):
        if self._output_p:
            self._local_dylib.ireeCompilerOutputDestroy(self._output_p)
            self._output_p = None

    @staticmethod
    def open_file(file_path: str) -> "Output":
        output_p = c_void_p()
        _handle_error(
            _dylib.ireeCompilerOutputOpenFile(file_path.encode(), byref(output_p))
        )
        return Output(output_p)

    @staticmethod
    def open_membuffer() -> "Output":
        output_p = c_void_p()
        _handle_error(_dylib.ireeCompilerOutputOpenMembuffer(byref(output_p)))
        return Output(output_p)

    def keep(self) -> "Output":
        _dylib.ireeCompilerOutputKeep(self._output_p)

    def write(self, buffer):
        _handle_error(
            _dylib.ireeCompilerOutputWrite(self._output_p, buffer, len(buffer))
        )

    def map_memory(self) -> memoryview:
        contents = c_void_p()
        size = c_uint64()
        _handle_error(
            _dylib.ireeCompilerOutputMapMemory(
                self._output_p, byref(contents), byref(size)
            )
        )
        size = size.value
        return memoryview((c_char * size).from_address(contents.value))


class Source:
    """Wraps an iree_compiler_source_t."""

    def __init__(self, session: Session, source_p: c_void_p, backing_ref):
        self._session: c_void_p = session  # Keeps ref alive.
        self._source_p: c_void_p = source_p
        self._backing_ref = backing_ref
        self._local_dylib = _dylib

    def __del__(self):
        self.close()

    def close(self):
        if self._source_p:
            s = self._source_p
            self._source_p = c_void_p()
            self._local_dylib.ireeCompilerSourceDestroy(s)
            self._backing_ref = None
            self._session = c_void_p()

    def __repr__(self):
        return f"<Source {self._source_p}>"

    @staticmethod
    def open_file(session: Session, file_path: str) -> "Source":
        source_p = c_void_p()
        _handle_error(
            _dylib.ireeCompilerSourceOpenFile(
                session._session_p, file_path.encode(), byref(source_p)
            )
        )
        return Source(session, source_p, None)

    @staticmethod
    def wrap_buffer(
        session: Session, buffer, *, buffer_name: Optional[str] = None
    ) -> "Source":
        view = memoryview(buffer)
        if not view.c_contiguous:
            raise ValueError("Buffer must be c_contiguous")
        source_p = c_void_p()
        buffer_len = len(buffer)
        _handle_error(
            _dylib.ireeCompilerSourceWrapBuffer(
                session._session_p,
                buffer_name.encode(),
                buffer,
                buffer_len,
                # Detect if nul terminated.
                True if buffer_len > 0 and view[-1] == 0 else False,
                byref(source_p),
            )
        )
        return Source(session, source_p, buffer)


class PipelineType(IntEnum):
    IREE_COMPILER_PIPELINE_STD = 0
    IREE_COMPILER_PIPELINE_HAL_EXECUTABLE = 1


class Invocation:
    def __init__(self, session: Session):
        self._session = session
        self._inv_p = _dylib.ireeCompilerInvocationCreate(self._session._session_p)
        self._sources: List[Source] = []
        self._local_dylib = _dylib

    def __del__(self):
        self.close()

    def close(self):
        if self._inv_p:
            self._local_dylib.ireeCompilerInvocationDestroy(self._inv_p)
            self._inv_p = c_void_p()
            for s in self._sources:
                s.close()
            self._sources.clear()

    def enable_console_diagnostics(self):
        _dylib.ireeCompilerInvocationEnableConsoleDiagnostics(self._inv_p)

    def parse_source(self, source: Source) -> bool:
        self._sources.append(source)
        return _dylib.ireeCompilerInvocationParseSource(self._inv_p, source._source_p)

    def execute(
        self, pipeline: PipelineType = PipelineType.IREE_COMPILER_PIPELINE_STD
    ) -> bool:
        return _dylib.ireeCompilerInvocationPipeline(self._inv_p, pipeline)

    def output_ir(self, output: Output):
        _handle_error(
            _dylib.ireeCompilerInvocationOutputIR(self._inv_p, output._output_p)
        )

    def output_vm_bytecode(self, output: Output):
        _handle_error(
            _dylib.ireeCompilerInvocationOutputVMBytecode(self._inv_p, output._output_p)
        )


def _probe_iree_compiler_dylib() -> str:
    """Probes an installed iree.compiler for the compiler dylib."""
    # TODO: Make this an API on iree.compiler itself. Burn this with fire.
    from iree.compiler import _mlir_libs

    try:
        from iree.compiler import version

        version_dict = version.VERSION
        dev_mode = False
    except ImportError:
        # Development setups often lack this.
        version_dict = {}
        dev_mode = True

    if dev_mode and len(_mlir_libs.__path__) == 1:
        # Track up the to the build dir and into the lib. Burn this with more fire.
        paths = [
            Path(_mlir_libs.__path__[0]).parent.parent.parent.parent.parent.parent
            / "lib"
        ]
    else:
        paths = _mlir_libs.__path__

    logging.debug("Found installed iree-compiler package %r", version_dict)
    dylib_basename = "libIREECompiler.so"
    system = platform.system()
    if system == "Darwin":
        dylib_basename = "libIREECompiler.dylib"
    elif system == "Windows":
        dylib_basename = "IREECompiler.dll"

    for p in paths:
        dylib_path = Path(p) / dylib_basename
        if dylib_path.exists():
            logging.debug("Found --iree-compiler-dylib=%s", dylib_path)
            return dylib_path
    raise ValueError(f"Could not find {dylib_basename} in {paths}")


class _GlobalInit:
    def __init__(self):
        _init_dylib()
        # Cache locally so as to not have it go out of scope first
        # during shutdown.
        self.local_dylib = _dylib
        self.local_dylib.ireeCompilerGlobalInitialize()

    def __del__(self):
        self.local_dylib.ireeCompilerGlobalShutdown()


# Keep one reference for the life of the module.
_global_init = _GlobalInit()
