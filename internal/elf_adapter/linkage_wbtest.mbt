///|
fn edited(
  bytes : Bytes,
  position : Int32,
  value : UInt64,
  width : Int32,
) -> Bytes {
  let copy = bytes.to_array()
  for i = 0; i < width; i = i + 1 {
    copy[position + i] = ((value >> (i * 8)) & 255).to_byte()
  }
  Bytes::from_array(copy[:])
}

///|
test "damaged version chains, symbol indices and hash filters cannot pass" {
  for arch in ["x86_64", "aarch64"] {
    let source = @fs.read_file_to_bytes("fixtures/generated/\{arch}/app")
    let frame = read_frame(source)
    let needs = at(frame, tag(frame, 0x6ffffffe), 0, 16)
    let versions = at(frame, tag(frame, 0x6ffffff0), 0, 2)
    let reloc = at(frame, tag(frame, 23), 0, 24)
    let broken = [
      edited(source, needs, 99, 2),
      edited(source, needs + 8, 0xfffffff0, 4),
      edited(source, needs + 12, 0xfffffff0, 4),
      edited(source, versions, 32767, 2),
      edited(source, reloc + 8, (99999UL << 32) | 7, 8),
    ]
    let library = @fs.read_file_to_bytes(
      "fixtures/generated/\{arch}/old/libdemo.so.1",
    )
    let frame = read_frame(library)
    let defs = at(frame, tag(frame, 0x6ffffffc), 0, 20)
    broken.push(edited(library, defs, 99, 2))
    broken.push(edited(library, defs + 12, 0xfffffff0, 4))
    let hash = at(frame, tag(frame, 0x6ffffef5), 0, 24)
    broken.push(edited(library, hash + 16, 0, 8))
    for data in broken {
      try read_linkage(data) catch {
        @model.ElfError::Malformed(_) => ()
        _ => fail("wrong malformed-input category")
      } noraise {
        _ => fail("damaged runtime metadata accepted")
      }
    }
  }
}
