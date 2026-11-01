///|
pub(all) suberror SnapshotError {
  InvalidSnapshot(String)
  ContentMismatch(String)
  SnapshotLimit(String)
}

///|
/// The first profile deliberately describes an explicit, cache-disabled run.
/// Paths are lowercase hexadecimal encodings of Linux filename bytes.
pub(all) struct Profile {
  rule_revision : String
  loader_family : String
  machine : Int32
  loader_path_hex : String
  loader_sha256 : String
  cwd_hex : String
  default_dirs_hex : Array[String]
  library_path_hex : Array[String]
  cache_mode : String
  hwcaps_policy : String
  secure_execution : Bool
  preload : Array[String]
  audit : Array[String]
} derive(ToJson, @json.FromJson)

///|
pub extend Profile with ToJson::{to_json}

///|
pub extend Profile with @json.FromJson::{from_json}

///|
pub(all) struct ManifestEntry {
  path_hex : String
  kind : String
  file_id : String?
  sha256 : String?
  target_hex : String?
} derive(ToJson, @json.FromJson)

///|
pub extend ManifestEntry with ToJson::{to_json}

///|
pub extend ManifestEntry with @json.FromJson::{from_json}

///|
pub(all) struct Manifest {
  schema_version : Int32
  profile : Profile
  entries : Array[ManifestEntry]
} derive(ToJson, @json.FromJson)

///|
pub extend Manifest with ToJson::{to_json}

///|
pub extend Manifest with @json.FromJson::{from_json}

///|
pub struct Snapshot {
  profile : Profile
  filesystem : FileSystem
  contents : Map[String, Bytes]
  digests : Map[String, String]
  manifest_digest : String
}

///|
pub fn sha256(data : Bytes) -> String {
  @hex.encode(Bytes::from_array(@crypto.sha256(data)[:])[:])
}

///|
fn decode_hex(value : String) -> Bytes raise {
  let bytes = @hex.decode(value[:])
  guard @hex.encode(bytes[:]) == value else {
    raise InvalidSnapshot("hex strings must be lowercase and canonical")
  }
  bytes
}

///|
fn digest_valid(value : String) -> Unit raise {
  guard value.length() == 64 && decode_hex(value).length() == 32 else {
    raise InvalidSnapshot("invalid sha256 digest")
  }
}

///|
/// Validates all indexed content before analysis. The callback receives only a
/// validated 64-character digest, never an untrusted filesystem path.
pub fn load(
  manifest_json : String,
  read_blob : (String) -> Bytes raise,
) -> Snapshot raise {
  guard manifest_json.length() <= 4194304 else {
    raise SnapshotLimit("manifest exceeds 4 MiB")
  }
  let manifest : Manifest = @json.from_json(@json.parse(manifest_json[:]))
  guard manifest.schema_version == 1 else {
    raise InvalidSnapshot("unsupported snapshot schema")
  }
  guard manifest.entries.length() <= 20000 else {
    raise SnapshotLimit("more than 20000 entries")
  }
  let profile = manifest.profile
  guard profile.machine == 62 || profile.machine == 183 else {
    raise InvalidSnapshot("unsupported profile architecture")
  }
  let cwd = decode_hex(profile.cwd_hex)
  let loader = decode_hex(profile.loader_path_hex)
  guard !cwd.is_empty() &&
    cwd[0] == b'/' &&
    !loader.is_empty() &&
    loader[0] == b'/' else {
    raise InvalidSnapshot("cwd and loader must be absolute")
  }
  digest_valid(profile.loader_sha256)
  for value in profile.default_dirs_hex {
    let path = decode_hex(value)
    guard !path.is_empty() && path[0] == b'/' else {
      raise InvalidSnapshot("default directories must be absolute")
    }
    ignore(parts(path))
  }
  guard profile.default_dirs_hex.length() + profile.library_path_hex.length() <=
    1024 else {
    raise SnapshotLimit("too many profile search directories")
  }
  for value in profile.library_path_hex {
    let path = decode_hex(value)
    if !path.is_empty() {
      ignore(parts(path))
    }
  }
  let items = []
  let contents : Map[String, Bytes] = Map([])
  let digests : Map[String, String] = Map([])
  let blobs : Map[String, Bytes] = Map([])
  let mut total = 0
  for entry in manifest.entries {
    let path = decode_hex(entry.path_hex)
    let item = match
      (entry.kind, entry.file_id, entry.sha256, entry.target_hex) {
      ("directory", None, None, None) => Directory
      ("symlink", None, None, Some(target)) => Symlink(decode_hex(target))
      ("file", Some(id), Some(digest), None) => {
        guard !id.is_empty() && id.length() <= 256 else {
          raise InvalidSnapshot("invalid file identity")
        }
        digest_valid(digest)
        if digests.get(id) is Some(previous) {
          guard previous == digest else {
            raise ContentMismatch("file identity has conflicting content")
          }
        }
        let bytes = match blobs.get(digest) {
          Some(bytes) => bytes
          None => {
            let bytes = read_blob(digest)
            guard bytes.length() <= 134217728 &&
              bytes.length() <= 268435456 - total else {
              raise SnapshotLimit(
                "content exceeds 128 MiB/file or 256 MiB/snapshot",
              )
            }
            guard sha256(bytes) == digest else { raise ContentMismatch(digest) }
            total += bytes.length()
            blobs[digest] = bytes
            bytes
          }
        }
        contents[id] = bytes
        digests[id] = digest
        File(id)
      }
      _ => raise InvalidSnapshot("inconsistent manifest entry fields")
    }
    items.push((path, item))
  }
  let filesystem = FileSystem::new(items)
  guard filesystem.resolve(cwd).entry is Directory else {
    raise InvalidSnapshot("cwd is not a directory")
  }
  // A missing interpreter is a deployment finding. An indexed profile loader
  // with the wrong digest is corrupt evidence and is rejected here.
  try filesystem.resolve(loader) catch {
    PathError::MissingPath(_)
    | PathError::NotDirectory(_)
    | PathError::TooManyLinks => ()
    error => raise error
  } noraise {
    resolved =>
      if resolved.entry is File(id) {
        guard digests.get(id) == Some(profile.loader_sha256) else {
          raise ContentMismatch("profile loader identity")
        }
      }
  }
  {
    profile,
    filesystem,
    contents,
    digests,
    manifest_digest: sha256(@utf8.encode(manifest_json)),
  }
}

///|
pub fn Snapshot::profile(self : Snapshot) -> Profile {
  {
    ..self.profile,
    default_dirs_hex: self.profile.default_dirs_hex.copy(),
    library_path_hex: self.profile.library_path_hex.copy(),
    preload: self.profile.preload.copy(),
    audit: self.profile.audit.copy(),
  }
}

///|
pub fn Snapshot::manifest_digest(self : Snapshot) -> String {
  self.manifest_digest
}

///|
pub fn Snapshot::resolve(
  self : Snapshot,
  path : Bytes,
) -> Resolved raise PathError {
  // Validated when the snapshot is constructed.
  let cwd = try! @hex.decode(self.profile.cwd_hex[:])
  self.filesystem.resolve(path, cwd~)
}

///|
pub fn Snapshot::content(self : Snapshot, id : String) -> Bytes? {
  self.contents.get(id)
}

///|
pub fn Snapshot::digest(self : Snapshot, id : String) -> String? {
  self.digests.get(id)
}
