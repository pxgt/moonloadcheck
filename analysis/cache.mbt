///|
priv enum CacheState {
  Disabled
  Entries(Array[@cache.Record])
  Unknown
}

///|
fn read_cache(snapshot : @snapshot.Snapshot) -> CacheState raise {
  if snapshot.profile().cache_mode != "glibc-cache-v1" {
    return Disabled
  }
  let resolved = snapshot.resolve(b"/etc/ld.so.cache") catch {
    @snapshot.PathError::MissingPath(_) => return Entries([])
    _ => return Unknown
  }
  guard resolved.entry is @snapshot.Entry::File(id) else { return Unknown }
  let bytes = snapshot.content(id).unwrap()
  try @cache.decode(bytes) catch {
    @cache.CacheError::Unsupported(_) => Unknown
    @cache.CacheError::Invalid(message) =>
      raise @model.ElfError::Malformed(message)
  } noraise {
    records => Entries(records)
  }
}

///|
fn cache_candidate(
  cache : CacheState,
  profile : @snapshot.Profile,
  needed : Bytes,
  no_defaults : Bool,
) -> (String, Bytes)? {
  let selected = match cache {
    Disabled => return None
    Unknown => return Some(("cache_unknown", b"/etc/ld.so.cache"))
    Entries(records) =>
      @cache.select(records, needed, profile.machine) catch {
        _ => return Some(("cache_unknown", b"/etc/ld.so.cache"))
      }
  }
  guard selected is Some(path) else { return None }
  if no_defaults {
    for hex in profile.default_dirs_hex {
      let dir = try! @hex.decode(hex[:])
      let prefix = if dir[dir.length() - 1] == b'/' {
        dir
      } else {
        concat(dir, b"/")
      }
      if path.length() >= prefix.length() && path[:prefix.length()] == prefix[:] {
        // glibc filters the one selected path; it does not ask for the next
        // cache record after a NODEFLIB rejection.
        return Some(("cache_nodeflib", path))
      }
    }
  }
  Some(("cache", path))
}
