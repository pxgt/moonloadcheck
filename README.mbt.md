# MoonLoadCheck library example

The current library provides a host-independent Linux file namespace. This
example resolves an absolute symlink inside that namespace without touching
the host filesystem. It does not perform a compatibility check.

```mbt check
///|
test "public namespace example" {
  let files = @moonloadcheck.FileSystem::new([
    (b"/lib", @moonloadcheck.Entry::Directory),
    (b"/lib/example.so", @moonloadcheck.Entry::File("library-object")),
    (b"/alias", @moonloadcheck.Entry::Symlink(b"/lib")),
  ])
  let resolved = files.resolve(b"/alias/example.so")
  assert_eq(resolved.path, b"/lib/example.so")
  assert_true(resolved.entry is @moonloadcheck.Entry::File("library-object"))
}
```
