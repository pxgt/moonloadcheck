# MoonLoadCheck library example

The library provides a host-independent Linux file namespace. This
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

After generating the reference fixtures, this example checks a captured target
through the public facade and reads the resulting report without reanalysis.
The callback reads only hash-named blobs. A CLI/application can apply its own
bounded storage reader; the analyzer performs the hash checks.

```mbt check
///|
test "public deployment and offline report API" {
  let folder = "fixtures/generated/u2/x86_64/used-export-removed/snapshot/"
  let target = @moonloadcheck.load_snapshot(
    @fs.read_file_to_string(folder + "manifest.json"),
    digest => @fs.read_file_to_bytes(folder + "blobs/" + digest),
  )
  let report = @moonloadcheck.check_compatibility(target, b"/opt/demo/app")
  assert_eq(report.exit_code(), 1)
  let saved = @moonloadcheck.read_report(report.to_json().stringify())
  let finding = saved.explain(report.findings[0].id)
  assert_eq(finding.code, "MLC005")
}
```
