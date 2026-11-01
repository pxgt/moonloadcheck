///|
pub(all) suberror ElfError {
  Malformed(String)
  Unsupported(String)
  ResourceLimit(String)
}

///|
/// Runtime dependency metadata; byte strings are never decoded for comparison.
pub(all) struct ElfObject {
  machine : Int32
  object_type : Int32
  interpreter : Bytes?
  needed : Array[Bytes]
  soname : Bytes?
  rpath : Bytes?
  runpath : Bytes?
  no_default_lib : Bool
  pie : Bool
  unsupported : Array[String]
} derive(Eq)

///|
pub extend ElfObject with Eq::{equal, not_equal}
