///|
fn sample() -> @snapshot.FileSystem raise {
  @snapshot.FileSystem::new([
    (b"/usr", @snapshot.Directory),
    (b"/usr/lib", @snapshot.Directory),
    (b"/usr/lib/libdemo.so", @snapshot.File("library")),
    (b"/usr/marker", @snapshot.File("usr-marker")),
    (b"/marker", @snapshot.File("root-marker")),
    (b"/lib", @snapshot.Symlink(b"usr/lib")),
    (b"/absolute", @snapshot.Symlink(b"/usr/lib")),
    (b"/broken", @snapshot.Symlink(b"/missing")),
    (b"/cycle-a", @snapshot.Symlink(b"cycle-b")),
    (b"/cycle-b", @snapshot.Symlink(b"cycle-a")),
    (b"/UPPER", @snapshot.File("upper")),
    (b"/upper", @snapshot.File("lower")),
    (b"/\xff", @snapshot.File("non-utf8")),
    (b"/alias", @snapshot.File("library")),
    (b"/identical-copy", @snapshot.File("distinct-file")),
    (b"/file-link", @snapshot.Symlink(b"/marker/")),
  ])
}

///|
test "relative and absolute symlinks stay in the target namespace" {
  let fs = sample()
  for path in [b"/lib/libdemo.so", b"/absolute/libdemo.so"] {
    let result = fs.resolve(path)
    assert_eq(result.path, b"/usr/lib/libdemo.so")
    assert_true(result.entry is @snapshot.File("library"))
    assert_eq(result.symlinks, 1)
  }
}

///|
test "dotdot is applied after symlink expansion" {
  let result = sample().resolve(b"/lib/../marker")
  assert_eq(result.path, b"/usr/marker")
  assert_true(result.entry is @snapshot.File("usr-marker"))
}

///|
test "relative path uses declared cwd and root dotdot stays at root" {
  let fs = sample()
  assert_eq(fs.resolve(b"../marker", cwd=b"/lib").path, b"/usr/marker")
  assert_eq(fs.resolve(b"/../../../marker").path, b"/marker")
  assert_eq(
    fs.resolve(b"//usr///lib/./libdemo.so").path,
    b"/usr/lib/libdemo.so",
  )
}

///|
test "case and non-UTF8 names are lossless" {
  let fs = sample()
  assert_true(fs.resolve(b"/UPPER").entry is @snapshot.File("upper"))
  assert_true(fs.resolve(b"/upper").entry is @snapshot.File("lower"))
  assert_true(fs.resolve(b"/\xff").entry is @snapshot.File("non-utf8"))
}

///|
test "file identity is separate from path spelling and contents" {
  let fs = sample()
  assert_true(fs.resolve(b"/alias").entry is @snapshot.File("library"))
  assert_true(
    fs.resolve(b"/identical-copy").entry is @snapshot.File("distinct-file"),
  )
}

///|
test "file followed by dotdot or trailing slash is not a directory" {
  let fs = sample()
  for path in [b"/marker/..", b"/marker/", b"/file-link"] {
    let rejected = try {
      ignore(fs.resolve(path))
      false
    } catch {
      @snapshot.PathError::NotDirectory(_) => true
      _ => false
    }
    assert_true(rejected)
  }
}

///|
test "broken links and link cycles have different errors" {
  let fs = sample()
  let missing = try {
    ignore(fs.resolve(b"/broken"))
    false
  } catch {
    @snapshot.PathError::MissingPath(_) => true
    _ => false
  }
  let cycle = try {
    ignore(fs.resolve(b"/cycle-a"))
    false
  } catch {
    @snapshot.PathError::TooManyLinks => true
    _ => false
  }
  assert_true(missing && cycle)
}

///|
test "invalid entries and resource limits never resolve successfully" {
  let duplicate = try {
    ignore(
      @snapshot.FileSystem::new([
        (b"/a", @snapshot.File("a")),
        (b"/a", @snapshot.File("b")),
      ]),
    )
    false
  } catch {
    @snapshot.PathError::DuplicatePath(_) => true
    _ => false
  }
  let nul = try {
    ignore(sample().resolve(b"/\x00"))
    false
  } catch {
    @snapshot.PathError::InvalidPath(_) => true
    _ => false
  }
  let limited = try {
    ignore(sample().resolve(b"/usr/lib/libdemo.so", max_steps=1))
    false
  } catch {
    @snapshot.PathError::TooManySteps => true
    _ => false
  }
  assert_true(duplicate && nul && limited)
}
