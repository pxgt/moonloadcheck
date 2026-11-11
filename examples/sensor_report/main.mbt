///|
extern "C" fn calibrate(raw : Int32) -> Int32 = "sensor_calibrate"

///|
extern "C" fn exit_process(code : Int32) -> Unit = "exit"

///|
priv suberror InputError {
  InputError(String)
}

///|
fn summarize(input : String) -> Json raise {
  let readings = input.split(",").collect()
  guard readings.length() > 0 && readings.length() <= 1000 else {
    raise InputError("expected 1..1000 comma-separated milli-Celsius readings")
  }
  let mut total = 0
  let mut minimum = 100251
  let mut maximum = -100001
  for item in readings {
    let raw = @string.parse_int(item, base=10)
    guard raw >= -50000 && raw <= 100000 else {
      raise InputError("reading outside -50000..100000 milli-Celsius")
    }
    let corrected = calibrate(raw)
    total += corrected
    minimum = if corrected < minimum { corrected } else { minimum }
    maximum = if corrected > maximum { corrected } else { maximum }
  }
  {
    "samples": readings.length(),
    "min_milli_c": minimum,
    "max_milli_c": maximum,
    "mean_milli_c": total / readings.length(),
  }
}

///|
fn main {
  let args = @env.args()
  if args.length() != 2 {
    println("usage: sensor-report MILLI_C,MILLI_C,...")
    exit_process(2)
  } else {
    try summarize(args[1]) catch {
      error => {
        println(Json::string(error.to_string()).stringify())
        exit_process(2)
      }
    } noraise {
      report => println(report.stringify())
    }
  }
}
