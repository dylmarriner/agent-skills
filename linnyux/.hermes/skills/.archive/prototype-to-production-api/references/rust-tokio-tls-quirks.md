# Rust Tokio-TLS / rusb Build Quirks

## tokio-rustls Server Type Mismatch

When building a TLS server with `tokio-rustls 0.26.x`, the accepted TLS stream from `TlsAcceptor::accept()` returns `tokio_rustls::server::TlsStream<T>`, but the top-level module's `TlsStream` enum has `Server` and `Client` variants.

**Wrong:**
```rust
async fn handle_implant(stream: tokio_rustls::TlsStream<TcpStream>) { ... }
// ...
handle_implant(tls_stream, ...).await;  // tls_stream is server::TlsStream, not TlsStream
```

**Fix — use the server type directly:**
```rust
async fn handle_implant(stream: tokio_rustls::server::TlsStream<TcpStream>) { ... }
```

## PrivateKeyDer Wrapping

`rustls_pemfile::pkcs8_private_keys()` returns `Vec<PrivatePkcs8KeyDer>`, but `ServerConfig::with_single_cert()` expects `PrivateKeyDer`.

**Wrong:**
```rust
.with_single_cert(certs, keys.into_iter().next().unwrap())
```

**Fix — wrap in Pkcs8 variant:**
```rust
use rustls::pki_types::PrivateKeyDer;
.with_single_cert(certs, PrivateKeyDer::Pkcs8(keys.into_iter().next().unwrap()))
```

## rustls crate version mismatch

`ServerConfig::builder()` moved to a different path across rustls versions. In `rustls 0.23.x`:
```rust
use tokio_rustls::rustls::ServerConfig;
let config = ServerConfig::builder()
    .with_no_client_auth()
    .with_single_cert(certs, key)?;
```

The `with_no_client_auth()` call was added in 0.23 as a replacement for the implicit client-auth default.

## rusb vs serialport

| Use Case | Crate | Notes |
|----------|-------|-------|
| CDC ACM (virtual serial) | `serialport = "4"` | Open by path (`/dev/ttyACM0`), baud 115200, timeout. Simple text commands. |
| Vendor-specific bulk endpoints | `rusb = "0.9"` | Find by VID/PID, claim interface, bulk write/read. Binary protocols. |
