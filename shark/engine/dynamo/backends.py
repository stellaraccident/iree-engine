# Copyright 2023 Stella Laurenzo
#
# Licensed under the Apache License v2.0 with LLVM Exceptions.
# See https://llvm.org/LICENSE.txt for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

# from torch._dynamo.optimizations import register_backend

import torch_mlir
from torch_mlir.dynamo import make_simple_dynamo_backend


# TODO: We probably want to decompose the magic make_simple_dynamo_backend
# and torch_mlir.compile to customize to our use cases. But works ok for now.
@make_simple_dynamo_backend
def _real_backend(gm, example_inputs):
    print("_backend() called with FX graph:")
    print(example_inputs)
    gm.print_readable()
    module = torch_mlir.compile(gm, example_inputs, output_type="linalg-on-tensors")
    print(module)
    # TODO: Don't just delegate to the eager executor.
    return gm.forward  # return a python callable


_backend = _real_backend


def cpu_sync(gm, example_inputs):
    return _backend(gm, example_inputs)


def cpu_threaded(gm, example_inputs):
    return _backend(gm, example_inputs)


def cuda(gm, example_inputs):
    return _backend(gm, example_inputs)
