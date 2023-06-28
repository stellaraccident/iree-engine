# Copyright 2023 Stella Laurenzo
#
# Licensed under the Apache License v2.0 with LLVM Exceptions.
# See https://llvm.org/LICENSE.txt for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""Dynamic library binding to libIREECompiler.so, using ctypes."""

from pathlib import Path
from typing import Sequence

import ctypes
import logging
import os
import platform

__all__ = [
    "Invocation",
    "Session",
]

_dylib = None

_GET_FLAG_CALLBACK = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_size_t,
                                      ctypes.c_void_p)


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
  _dylib = ctypes.cdll.LoadLibrary(dylib_path)

  # Setup signatures.
  # Error
  _setsig(_dylib.ireeCompilerErrorDestroy, None, [ctypes.c_void_p])
  _setsig(_dylib.ireeCompilerErrorGetMessage, ctypes.c_char_p,
          [ctypes.c_void_p])
  # Invocation
  _setsig(_dylib.ireeCompilerInvocationCreate, ctypes.c_void_p,
          [ctypes.c_void_p])
  _setsig(_dylib.ireeCompilerInvocationDestroy, None, [ctypes.c_void_p])
  # Session
  _setsig(_dylib.ireeCompilerSessionCreate, ctypes.c_void_p, [])
  _setsig(_dylib.ireeCompilerSessionDestroy, None, [ctypes.c_void_p])
  _setsig(_dylib.ireeCompilerSessionGetFlags, None,
          [ctypes.c_void_p, ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p])
  _setsig(_dylib.ireeCompilerSessionSetFlags, ctypes.c_void_p,
          [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p])
  # Source
  _setsig(_dylib.ireeCompilerSourceWrapBuffer, ctypes.c_void_p, [
    ctypes.c_void_p, # session
    ctypes.c_void_p, # bufferName
    ctypes.c_void_p, # buffer
    ctypes.c_size_t, # length
    ctypes.c_bool, # isNullTerminated
    ctypes.c_void_p, # out_source
  ])

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
      flag_bytes = ctypes.string_at(flag_pointer, length)
      flag_value = flag_bytes.decode("UTF-8")
      results.append(flag_value)

    _dylib.ireeCompilerSessionGetFlags(self._session_p, non_default_only,
                                             callback, ctypes.c_void_p(0))
    return results

  def set_flags(self, *flags: Sequence[str]):
    argv_type = ctypes.c_char_p * len(flags)
    argv = argv_type(*[flag.encode("UTF-8") for flag in flags])
    _handle_error(
        _dylib.ireeCompilerSessionSetFlags(self._session_p, len(argv),
                                                 argv))


class Invocation:

  def __init__(self, session: Session):
    self._session = session
    self._inv_p = _dylib.ireeCompilerInvocationCreate(
        self._session._session_p)

  def __del__(self):
    _dylib.ireeCompilerInvocationDestroy(self._inv_p)


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
    paths = [Path(_mlir_libs.__path__[0]).parent.parent.parent.parent.parent.parent / "lib"]
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
    _dylib.ireeCompilerGlobalInitialize()

  def __del__(self):
    _dylib.ireeCompilerGlobalShutdown()


# Keep one reference for the life of the module.
_global_init = _GlobalInit()
