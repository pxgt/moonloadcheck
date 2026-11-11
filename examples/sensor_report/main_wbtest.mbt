///|
test "calibrated report and bounded fixed point arithmetic" {
  json_inspect(summarize("19500,22000,24500"), content={
    "samples": 3,
    "min_milli_c": 19750,
    "max_milli_c": 24750,
    "mean_milli_c": 22250,
  })
  json_inspect(summarize("100000"), content={
    "samples": 1,
    "min_milli_c": 100250,
    "max_milli_c": 100250,
    "mean_milli_c": 100250,
  })
  json_inspect(summarize("-50000"), content={
    "samples": 1,
    "min_milli_c": -49750,
    "max_milli_c": -49750,
    "mean_milli_c": -49750,
  })
}

///|
test "invalid sensor input is rejected" {
  for input in ["", "1,", "nan", "100001", "-50001"] {
    try summarize(input) catch {
      _ => ()
    } noraise {
      _ => fail("accepted invalid reading: " + input)
    }
  }
}
