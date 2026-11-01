///|
pub(all) enum Entry {
  Directory
  File(String)
  Symlink(Bytes)
}

///|
pub(all) suberror PathError {
  InvalidPath(Bytes)
  DuplicatePath(Bytes)
  MissingPath(Bytes)
  NotDirectory(Bytes)
  TooManyLinks
  TooManySteps
}

///|
/// A Linux namespace independent of the analysis host's filesystem.
pub struct FileSystem {
  entries : Map[Bytes, Entry]
}

///|
pub(all) struct Resolved {
  path : Bytes
  entry : Entry
  symlinks : Int32
}

///|
fn parts(path : Bytes) -> Array[Bytes] raise PathError {
  guard !path.is_empty() && path.length() <= 1048576 else {
    raise InvalidPath(path)
  }
  let result = []
  let mut start = 0
  for i = 0; i <= path.length(); i = i + 1 {
    if i < path.length() && path[i] == 0 {
      raise InvalidPath(path)
    }
    if i == path.length() || path[i] == b'/' {
      if start < i {
        result.push(path[start:i].to_owned())
      }
      start = i + 1
    }
  }
  result
}

///|
fn joined(components : Array[Bytes]) -> Bytes {
  let data : Array[Byte] = [b'/']
  for i = 0; i < components.length(); i = i + 1 {
    if i > 0 {
      data.push(b'/')
    }
    for byte in components[i] {
      data.push(byte)
    }
  }
  Bytes::from_array(data[:])
}

///|
/// Entries describe physical paths. Intermediate entry parents must be
/// directories; symlink aliases are resolved at lookup time, not indexed twice.
pub fn FileSystem::new(
  items : Array[(Bytes, Entry)],
) -> FileSystem raise PathError {
  let entries : Map[Bytes, Entry] = Map([])
  for (path, entry) in items {
    let components = parts(path)
    guard path[0] == b'/' && joined(components) == path else {
      raise InvalidPath(path)
    }
    for component in components {
      guard component != b"." && component != b".." else {
        raise InvalidPath(path)
      }
    }
    guard entries.get(path) is None else { raise DuplicatePath(path) }
    if path == b"/" {
      guard entry is Directory else { raise NotDirectory(path) }
    }
    if entry is Symlink(target) {
      ignore(parts(target))
    }
    entries[path] = entry
  }
  if entries.get(b"/") is None {
    entries[b"/"] = Directory
  }
  for path, _ in entries {
    let components = parts(path)
    if !components.is_empty() {
      ignore(components.pop())
      let parent = joined(components)
      match entries.get(parent) {
        Some(Directory) => ()
        Some(_) => raise NotDirectory(parent)
        None => raise MissingPath(parent)
      }
    }
  }
  { entries, }
}

///|
/// Resolve components in Linux order. In particular, `link/..` follows `link`
/// before applying `..`; lexical normalization would produce a different file.
pub fn FileSystem::resolve(
  self : FileSystem,
  path : Bytes,
  cwd~ : Bytes = b"/",
  max_links~ : Int32 = 40,
  max_steps~ : Int32 = 4096,
) -> Resolved raise PathError {
  guard max_links >= 0 && max_steps > 0 else { raise InvalidPath(path) }
  let request = parts(path)
  let mut pending = if path[0] == b'/' {
    request
  } else {
    let initial = parts(cwd)
    guard cwd[0] == b'/' else { raise InvalidPath(cwd) }
    for component in request {
      initial.push(component)
    }
    initial
  }
  let resolved = []
  let mut links = 0
  let mut steps = 0
  let mut index = 0
  let mut directory_required = path[path.length() - 1] == b'/'
  while index < pending.length() {
    steps += 1
    guard steps <= max_steps else { raise TooManySteps }
    let parent = joined(resolved)
    match self.entries.get(parent) {
      Some(Directory) => ()
      Some(_) => raise NotDirectory(parent)
      None => raise MissingPath(parent)
    }
    let component = pending[index]
    if component == b"." {
      index += 1
      continue
    }
    if component == b".." {
      ignore(resolved.pop())
      index += 1
      continue
    }
    resolved.push(component)
    let candidate = joined(resolved)
    let entry = match self.entries.get(candidate) {
      Some(entry) => entry
      None => raise MissingPath(candidate)
    }
    if entry is Symlink(target) {
      links += 1
      guard links <= max_links else { raise TooManyLinks }
      ignore(resolved.pop())
      if target[0] == b'/' {
        resolved.clear()
      }
      let replacement = parts(target)
      if index + 1 == pending.length() && target[target.length() - 1] == b'/' {
        directory_required = true
      }
      for j = index + 1; j < pending.length(); j = j + 1 {
        replacement.push(pending[j])
      }
      pending = replacement
      index = 0
    } else {
      index += 1
    }
  }
  let result = joined(resolved)
  let entry = match self.entries.get(result) {
    Some(entry) => entry
    None => raise MissingPath(result)
  }
  if directory_required {
    guard entry is Directory else { raise NotDirectory(result) }
  }
  { path: result, entry, symlinks: links, }
}
