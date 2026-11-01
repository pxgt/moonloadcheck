///|
priv suberror UnmodeledPath {
  UnmodeledPath(String)
}

///|
fn concat(a : Bytes, b : Bytes) -> Bytes {
  let bytes = []
  for value in a {
    bytes.push(value)
  }
  for value in b {
    bytes.push(value)
  }
  Bytes::from_array(bytes[:])
}

///|
fn absolute(path : Bytes, cwd : Bytes) -> Bytes {
  if !path.is_empty() && path[0] == b'/' {
    path
  } else {
    concat(concat(cwd, b"/"), path)
  }
}

///|
fn directory(path : Bytes) -> Bytes {
  let mut last = 0
  for i = 0; i < path.length(); i = i + 1 {
    if path[i] == b'/' {
      last = i
    }
  }
  if last == 0 {
    b"/"
  } else {
    path[:last].to_owned()
  }
}

///|
fn contains(path : Bytes, byte : Byte) -> Bool {
  for value in path {
    if value == byte {
      return true
    }
  }
  false
}

///|
fn token_character(c : Byte) -> Bool {
  (c >= b'A' && c <= b'Z') ||
  (c >= b'a' && c <= b'z') ||
  (c >= b'0' && c <= b'9') ||
  c == b'_'
}

///|
/// Token recognition is greedy: $ORIGIN_suffix is not $ORIGIN + _suffix.
fn expand(
  value : Bytes,
  origin : Bytes,
  profile : @snapshot.Profile,
) -> Bytes raise UnmodeledPath {
  guard value.length() <= 1048576 else {
    raise UnmodeledPath("path exceeds 1 MiB")
  }
  let result = []
  let mut i = 0
  while i < value.length() {
    if value[i] != b'$' {
      result.push(value[i])
      i += 1
      continue
    }
    let start = i
    let mut token_name = b""
    i += 1
    if i < value.length() && value[i] == b'{' {
      i += 1
      let token = i
      while i < value.length() && value[i] != b'}' {
        i += 1
      }
      guard i < value.length() else {
        raise UnmodeledPath("unterminated dynamic token")
      }
      token_name = value[token:i].to_owned()
      i += 1
    } else {
      while i < value.length() && token_character(value[i]) {
        i += 1
      }
      token_name = value[start + 1:i].to_owned()
    }
    let replacement = if token_name == b"ORIGIN" {
      origin
    } else {
      let hex = if token_name == b"LIB" {
        profile.lib_token_hex
      } else if token_name == b"PLATFORM" {
        profile.platform_token_hex
      } else {
        None
      }
      guard hex is Some(hex) else {
        raise UnmodeledPath("dynamic token lacks explicit target evidence")
      }
      try! @hex.decode(hex[:])
    }
    for byte in replacement {
      result.push(byte)
    }
    guard result.length() <= 1048576 else {
      raise UnmodeledPath("expanded path exceeds 1 MiB")
    }
  }
  Bytes::from_array(result[:])
}

///|
fn path_list(
  value : Bytes,
  origin : Bytes,
  profile : @snapshot.Profile,
) -> Array[Bytes] raise UnmodeledPath {
  if value.is_empty() {
    return []
  }
  let paths = []
  let mut start = 0
  for i = 0; i <= value.length(); i = i + 1 {
    if i == value.length() || value[i] == b':' || value[i] == b';' {
      paths.push(expand(value[start:i].to_owned(), origin, profile))
      guard paths.length() <= 1024 else {
        raise UnmodeledPath("search list exceeds 1024 entries")
      }
      start = i + 1
    }
  }
  paths
}
