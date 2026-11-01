///|
/// M0 observations of the upstream parser, not a compatibility verdict.
pub(all) struct Observation {
  machine : Int32
  has_sections : Bool
  dynamic_entries : Int32
  dynamic_symbols : Int32?
  version_requirements : Array[String]
} derive(ToJson)

///|
pub extend Observation with ToJson::{to_json}

///|
pub fn observe(data : Bytes) -> Observation raise @elf.ParseError {
  let elf = @elf.ElfBytes::minimal_parse(data[:])
  let mut dynamic_entries = 0
  if elf.dynamic() is Some(table) {
    for i = 0; i < table.len(); i = i + 1 {
      let item = table.get(i)
      if item.d_tag == @elf.DT_NULL {
        break
      }
      dynamic_entries += 1
    }
  }
  let versions = elf.symbol_version_table()
  let mut dynamic_symbols = None
  let version_requirements = []
  if elf.dynamic_symbol_table() is Some((symbols, strings)) {
    dynamic_symbols = Some(symbols.len())
    for i = 0; i < symbols.len(); i = i + 1 {
      let symbol = symbols.get(i)
      // Force checked access to each name instead of silently ending an iterator.
      ignore(strings.get_raw(symbol.st_name.reinterpret_as_int()))
      if symbol.is_undefined() {
        if versions is Some(table) {
          if table.get_requirement(i) is Some(requirement) {
            version_requirements.push(requirement.file + ":" + requirement.name)
          }
        }
      }
    }
  }
  {
    machine: elf.ehdr.e_machine.to_int(),
    has_sections: elf.section_headers() is Some(_),
    dynamic_entries,
    dynamic_symbols,
    version_requirements,
  }
}
