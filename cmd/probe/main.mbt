///|
fn main {
  let args = @env.args()
  if args.length() < 2 || args[args.length() - 2] != "--file" {
    println("usage: probe --file <ELF-file>; M0 observations only")
    @sys.exit(3)
  }
  try {
    let observed = @observation.observe(
      @fs.read_file_to_bytes(args[args.length() - 1]),
    )
    println(observed.to_json().stringify())
  } catch {
    error => {
      println("input_error: \{error}")
      @sys.exit(3)
    }
  }
}
