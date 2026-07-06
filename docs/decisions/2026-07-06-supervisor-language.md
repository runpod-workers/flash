# Supervisor language: Go vs Rust

## Decision

**Go.**

## Spike

Built the smallest possible "print a line, spawn a subprocess, exchange one
JSON line over a Unix domain socket" prototype in both languages (throwaway,
not committed). Measured static `linux/amd64` binaries:

| Language | Binary size (static, linux/amd64) | LOC | Build command |
|----------|-----------------------------------|-----|----------------|
| Go       | 4,194,378 bytes (~4.0 MiB)         | 51  | `CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build` |
| Rust     | 671,336 bytes (~656 KiB)           | 34  | `cargo build --release --target x86_64-unknown-linux-musl` |

Both binaries are fully static (Go: `statically linked`; Rust:
`static-pie linked` against musl) and both prototypes ran correctly,
printing the startup line, the subprocess output, and the decoded JSON
line received over the socket.

### Build toolchain friction

- **Go**: cross-compiling to static `linux/amd64` from macOS/arm64 worked
  immediately with only stdlib and two environment variables
  (`CGO_ENABLED=0 GOOS=linux GOARCH=amd64`) — no extra toolchain, no
  network access required beyond the existing Go install.
- **Rust**: cross-compiling to static `linux/amd64` from macOS/arm64
  required installing a musl cross-linker toolchain
  (`brew install FiloSottile/musl-cross/musl-cross`, a ~954 MB download)
  and wiring it into `.cargo/config.toml` (`target.x86_64-unknown-linux-musl.linker
  = "x86_64-linux-musl-gcc"`) before the target would link. The
  `rustup target add x86_64-unknown-linux-musl` step alone was not
  sufficient.

## Rationale

Rust produced the smaller binary (~656 KiB vs ~4.0 MiB) and slightly fewer
lines of code, but neither difference is decisive: a few megabytes is
negligible against the cold-start budget, which is dominated by image pull
and dependency installation, not supervisor binary size. What is decisive
is build friction — Go cross-compiles to a static `linux/amd64` binary with
zero extra tooling, while Rust required installing and wiring up a
dedicated musl cross-toolchain before it would even link, which is
additional operational surface for every dev machine and CI runner that
builds the capsule. Combined with the team's existing Go familiarity (per
engineer profile) and Tasks 1-6 already being planned in Go, the spike does
not show the "decisive, cold-start-relevant advantage" required to
overturn the default. **Go remains the supervisor language.**
