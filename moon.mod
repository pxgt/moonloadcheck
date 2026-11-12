// Learn more about moon.mod configuration:
// https://docs.moonbitlang.com/en/latest/toolchain/moon/module.html
//
// To add a dependency, run this command in your terminal:
//   moon add moonbitlang/x
//
// Or manually declare it in `import`, for example:
// import {
//   "moonbitlang/x@0.4.6",
// }

name = "Xpeng/moonloadcheck"

version = "0.3.0"

readme = "README.md"

repository = "https://github.com/pxgt/moonloadcheck"

license = "Apache-2.0"

keywords = [ "elf", "linux", "dynamic-linking", "compatibility" ]

preferred_target = "js"

description = "Offline Linux binary deployment compatibility analysis"

import {
  "moonbitlang/x@0.5.5",
  }
