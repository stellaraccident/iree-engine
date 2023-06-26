# IREE JIT Framework

The core `iree.compiler` and `iree.runtime` APIs form the foundation of
the compiler and runtime respectively, and these are sufficient APIs to
perform AOT and a variety of low level tasks. However, it is common to
require a higher-level API in order to manage arbitrary JIT workflows
which combine compilation, program transformation, and multi-device
execution. While many such runtime systems exist in frameworks and as
thick stacks of C++ code, the concepts are not actually very complicated,
and we seek to assemble them here in Python in a more inspectable and
hackable way.

