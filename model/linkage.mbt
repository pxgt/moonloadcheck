///|
pub(all) struct VersionNeed {
  provider : Bytes
  name : Bytes
  hash : UInt64
  index : Int32
  weak : Bool
  hidden : Bool
}

///|
pub(all) struct VersionDef {
  name : Bytes
  hash : UInt64
  index : Int32
  flags : Int32
}

///|
pub(all) struct DynamicSymbol {
  name : Bytes
  binding : Int32
  visibility : Int32
  kind : Int32
  section : Int32
  value : UInt64
  size : UInt64
  version_index : Int32
  version_hidden : Bool
  lookupable : Bool
}

///|
pub(all) struct Reference {
  symbol_index : Int32
  offset : UInt64
  relocation : Int32
  table : String
}

///|
pub(all) struct Linkage {
  object : ElfObject
  symbols : Array[DynamicSymbol]
  references : Array[Reference]
  version_needs : Array[VersionNeed]
  version_defs : Array[VersionDef]
  has_versions : Bool
  symbolic : Bool
  bind_now : Bool
}
