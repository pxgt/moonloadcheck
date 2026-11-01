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
pub using @model {type ElfObject, type ElfError, type Linkage}

///|
pub using @analysis {
  type Report,
  type Finding,
  type ImpactReport,
  type ReportError,
}

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

///|
pub fn read_linkage(data : Bytes) -> Linkage raise ElfError {
  @elf.read_linkage(data)
}

///|
pub fn check_compatibility(snapshot : Snapshot, entry : Bytes) -> Report {
  @analysis.check_compatibility(snapshot, entry)
}

///|
pub fn compare(
  before : Snapshot,
  after : Snapshot,
  entries : Array[Bytes],
) -> ImpactReport raise {
  @analysis.compare(before, after, entries)
}

///|
pub fn read_report(json : String) -> Report raise {
  @analysis.read_report(json)
}
