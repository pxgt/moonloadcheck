///|
/// Host-independent Linux namespace primitives.
pub using @snapshot {type Entry, type FileSystem, type Resolved, type PathError}

///|
pub using @snapshot {
  type Snapshot,
  type Profile,
  type Manifest,
  type ManifestEntry,
}

///|
pub using @model {type ElfObject, type ElfError}

///|
pub using @analysis {type Report}

///|
pub fn read_elf(data : Bytes) -> ElfObject raise ElfError {
  @elf.read(data)
}

///|
pub fn load_snapshot(
  manifest : String,
  read_blob : (String) -> Bytes raise,
) -> Snapshot raise {
  @snapshot.load(manifest, read_blob)
}

///|
pub fn check_dependencies(snapshot : Snapshot, entry : Bytes) -> Report {
  @analysis.check_dependencies(snapshot, entry)
}
