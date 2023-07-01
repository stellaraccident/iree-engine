# Copyright 2023 Stella Laurenzo
#
# Licensed under the Apache License v2.0 with LLVM Exceptions.
# See https://llvm.org/LICENSE.txt for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from ..script_importer import ScriptImporter, make_simple_dynamo_backend

# TODO: Work out the boxing/aot-autograd nonsense vs using this utility.
@make_simple_dynamo_backend
def backend(gm, example_inputs):
    #print(example_inputs)
    imp = ScriptImporter()
    bc = imp(gm, example_inputs)
    # TODO: Don't just delegate to the eager executor.
    #print("COMPILED BC:", bc)
    return gm.forward  # return a python callable
