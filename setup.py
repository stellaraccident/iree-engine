# Copyright 2023 Stella Laurenzo
#
# Licensed under the Apache License v2.0 with LLVM Exceptions.
# See https://llvm.org/LICENSE.txt for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import argparse
import json
import os
from setuptools import find_namespace_packages, setup

setup(
    name=f"iree-engine",
    version=f"0.1",
    packages=find_namespace_packages(include=[
        "iree.engine",
        "iree.engine.*",
    ],),
    install_requires=[
        "numpy",
        #"iree-compiler",
        #"iree-runtime",
    ],
    extras_require={
    },
)
