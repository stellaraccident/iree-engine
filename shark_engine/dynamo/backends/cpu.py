# Copyright 2023 Stella Laurenzo
#
# Licensed under the Apache License v2.0 with LLVM Exceptions.
# See https://llvm.org/LICENSE.txt for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import functools

from ..executor import DeviceState, InputModule, JittableExecutable
from ..script_importer import ScriptImporter, make_simple_dynamo_backend

import torch


# TODO: Work out the boxing/aot-autograd nonsense vs using this utility.
@make_simple_dynamo_backend
def backend(gm: torch.fx.GraphModule, example_inputs):
    # print(example_inputs)
    imp = ScriptImporter(text_mode=True)
    input_module = InputModule(imp(gm, example_inputs))
    print("INPUT MODULE:", input_module)
    device_state = _get_device_state()
    exe = JittableExecutable(
        input_module,
        device_state,
        compiler_flags=("--iree-hal-target-backends=llvm-cpu",),
    )
    return exe
    # return gm.forward  # return a python callable


# IREE runtime globals. For the CPU right now, there is no device selection,
# so it is easy.
@functools.lru_cache(maxsize=None)
def _get_device_state() -> DeviceState:
    return DeviceState(driver="local-task")
