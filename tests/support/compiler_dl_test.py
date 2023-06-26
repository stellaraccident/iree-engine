# Copyright 2023 Stella Laurenzo
#
# Licensed under the Apache License v2.0 with LLVM Exceptions.
# See https://llvm.org/LICENSE.txt for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import unittest

from iree.jit.support.compiler_dl import *


class FlagsTest(unittest.TestCase):

  def testDefaultFlags(self):
    session = Session()
    flags = session.get_flags()
    print(flags)
    self.assertIn("--iree-input-type=auto", flags)

  def testNonDefaultFlags(self):
    session = Session()
    flags = session.get_flags(non_default_only=True)
    self.assertEqual(flags, [])
    session.set_flags("--iree-input-type=none")
    flags = session.get_flags(non_default_only=True)
    self.assertIn("--iree-input-type=none", flags)

  def testFlagsAreScopedToSession(self):
    session1 = Session()
    session2 = Session()
    session1.set_flags("--iree-input-type=tosa")
    session2.set_flags("--iree-input-type=none")
    self.assertIn("--iree-input-type=tosa",
                  session1.get_flags())
    self.assertIn("--iree-input-type=none",
                  session2.get_flags())

  def testFlagError(self):
    session = Session()
    with self.assertRaises(ValueError):
      session.set_flags("--does-not-exist=1")

class InvocationTest(unittest.TestCase):

  def testCreate(self):
    session = Session()
    inv = session.invocation()


if __name__ == "__main__":
  unittest.main()
