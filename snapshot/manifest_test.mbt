///|
fn manifest(entries : Array[@snapshot.ManifestEntry]) -> @snapshot.Manifest {
  {
    schema_version: 1,
    entries,
    profile: {
      rule_revision: "glibc-2.35-controlled-v1",
      loader_family: "glibc",
      machine: 62,
      loader_path_hex: "2f6c6f61646572",
      loader_sha256: @snapshot.sha256(b"loader"),
      cwd_hex: "2f",
      default_dirs_hex: [],
      library_path_hex: [],
      cache_mode: "disabled",
      hwcaps_policy: "none",
      secure_execution: false,
      preload: [],
      audit: [],
      lib_token_hex: None,
      platform_token_hex: None,
    },
  }
}

///|
fn file(path : String, id : String, content : Bytes) -> @snapshot.ManifestEntry {
  {
    path_hex: path,
    kind: "file",
    file_id: Some(id),
    sha256: Some(@snapshot.sha256(content)),
    target_hex: None,
  }
}

///|
test "portable manifest verifies content while retaining distinct and hardlink identities" {
  let source = manifest([
    file("2f61", "one", b"same"),
    file("2f62", "two", b"same"),
    file("2f63", "one", b"same"),
  ])
  let mut reads = 0
  let snapshot = @snapshot.load(source.to_json().stringify(), _ => {
    reads += 1
    b"same"
  })
  assert_eq(reads, 1)
  assert_true(snapshot.resolve(b"/a").entry is @snapshot.Entry::File("one"))
  assert_true(snapshot.resolve(b"/b").entry is @snapshot.Entry::File("two"))
  assert_true(snapshot.resolve(b"/c").entry is @snapshot.Entry::File("one"))
  assert_eq(snapshot.content("one"), Some(b"same"))
}

///|
test "tampering and conflicting identity cannot enter an analysis" {
  let source = manifest([file("2f61", "one", b"expected")])
  try @snapshot.load(source.to_json().stringify(), _ => b"tampered") catch {
    @snapshot.SnapshotError::ContentMismatch(_) => ()
    _ => fail("wrong error category")
  } noraise {
    _ => fail("accepted tampered content")
  }
  let source = manifest([
    file("2f61", "one", b"expected"),
    file("2f62", "one", b"different"),
  ])
  try @snapshot.load(source.to_json().stringify(), _ => b"expected") catch {
    @snapshot.SnapshotError::ContentMismatch(_) => ()
    _ => fail("wrong error category")
  } noraise {
    _ => fail("accepted conflicting file identity")
  }
}

///|
test "blob names cannot escape the content store" {
  let source = manifest([
    {
      path_hex: "2f61",
      kind: "file",
      file_id: Some("one"),
      sha256: Some("../secret"),
      target_hex: None,
    },
  ])
  let mut called = false
  try
    @snapshot.load(source.to_json().stringify(), _ => {
      called = true
      b""
    })
  catch {
    _ => ()
  } noraise {
    _ => fail("accepted invalid digest")
  }
  assert_false(called)
}
