# SS7 Tracker — tools/ss7-tracker/

Mobile subscriber tracking via SS7/MAP over SIGTRAN (M3UA).
Path: `/home/lin/Documents/universal-unlock-suite/tools/ss7-tracker/`

## Purpose

SS7 mobile tracking and intelligence tool targeting HLR/MSC/VLR nodes.
Provides MAP protocol operations: subscriber location (ATI), SMS routing
(SRIforSM), SMS injection (ForwardSM), roaming number (PRN), and
subscriber data manipulation (ISD).

## Protocol Stack

```
    [MAP]     — 3GPP TS 29.002 operation codes + ASN.1 parameters
    [TCAP]    — ITU-T Q.773 transaction layer (Begin/Continue/End)
    [SCCP]    — ITU-T Q.713 connectionless (UDT) routing via GT+SSN
    [M3UA]    — RFC 4666 SIGTRAN adaptation (TCP, ASP handshake)
    [TCP]     — Raw socket to M3UA peer
```

All encoding is done in-process with raw BER; no external ASN.1 compiler.
The protocol modules live under `src/protocol/`:
- `ber.rs`        — BER TLV encode/decode + TBCD codec
- `m3ua.rs`       — M3UA message framing, TCP connection, ASP_UP/ASP_ACTIVE
- `sccp.rs`       — SCCP UDT message building (connectionless)
- `tcap.rs`       — TCAP Begin wrapper + Invoke component encoding
- `map.rs`        — MAP operation constants + param builders (ATI, SRIforSM, PRN, ISD)

The operations layer lives under `src/operations/`:
- `tracker.rs`    — locate_subscriber (ATI), sms_delivery_path (SRIforSM)
- `sms.rs`        — forward_short_message (SRIforSM + ForwardSM chain)
- `calls.rs`      — provide_roaming_number (PRN), insert_subscriber_data (ISD)

## CLI Commands

```bash
# locate — subscriber location via AnyTimeInterrogation
cargo run -- locate --msisdn 447700000001 \
    --m3ua-host 10.0.0.1 --m3ua-port 2905 \
    --local-gt 447700000001 --network-gt 447700000099

# sms-path — SMS delivery path via SRIforSM
cargo run -- sms-path --msisdn 447700000001

# forward-sms — inject SMS to subscriber
cargo run -- forward-sms --sender 447700000010 \
    --recipient 447700000001 --message "Hello"

# roam — get roaming number via PRN
cargo run -- roam --imsi 204081234567890

# call-forward — set call forwarding via ISD
cargo run -- call-forward --imsi 204081234567890 \
    --forward-to 447700000099
```

All commands output JSON to stdout. Errors printed to stderr, exit code 1.

## Architecture: send_tcap_map_request

Every SS7 operation follows the same pattern via the shared
`send_tcap_map_request()` helper in `operations/tracker.rs`:

1. **Connect** — `M3UAConnection::connect(host, port)` → TCP connect
2. **ASP handshake** — `asp_up()` (ASP_UP / ASP_UP_ACK) then
   `asp_active()` (ASP_ACTIVE / ASP_ACTIVE_ACK)
3. **Build payload** — MAP params → TCAP Begin → SCCP UDT
4. **Send** — Wrap in M3UA DATA message with PROTOCOL_DATA param
5. **Receive** — Read M3UA header + body, `M3UAMessage::decode()`
6. **Unwrap** — `strip_sccp_header()` → TCAP payload
7. **Parse** — `parse_tcap_begin_response()` → components
8. **Extract** — `parse_return_result()` → result data
9. **Decode** — Operation-specific BER parsing (e.g. `parse_ati_result`)

```rust
// Canonical call pattern
let response_tcap = send_tcap_map_request(
    &m3ua_host, m3ua_port, &local_gt, &network_gt,
    6,                                     // HLR SSN
    &tcap_data,                            // TCAP Begin bytes
)?;
let (_dtid, components) = parse_tcap_begin_response(&response_tcap)?;
let (_invoke_id, result_data) = parse_return_result(&components[0])?;
let info = parse_ati_result(msisdn, &result_data)?;
```

## Response Parsing

All response parsing uses `BerDecoder` from `protocol/ber.rs`:

**ATI result (locate):**
```
SEQUENCE {
  [0] IMSI (OCTET STRING)
  [1] LocationInfo (constructed): [0] MSC GT (TBCD), [1] VLR GT (TBCD)
  [2] SubscriberState (constructed): [0] assumedIdle, [1] camelBusy, etc.
}
```

**SRIforSM result (sms-path):**
```
SEQUENCE {
  [0] IMSI (OCTET STRING)
  [1] LocationInfoWithPDN (constructed): [0] MSC GT (TBCD), [1] VLR GT (TBCD)
  [2] ServiceCentreAddressOA (optional)
}
```

**PRN result (roam):**
```
SEQUENCE {
  [0] roamingNumber (ISDN-AddressString, TBCD encoded)
}
```

## Build History / Known Issues

1. **tbcd.rs was missing** — `protocol/mod.rs` declared `pub mod tbcd;`
   referencing `TbcdCodec` from `ber.rs`, but the file didn't exist.
   Created `src/protocol/tbcd.rs` as a re-export: `pub use super::ber::TbcdCodec;`

2. **ToSocketAddrs trait mismatch** — M3UA connect used
   `TcpStream::connect(addrs)` where `addrs` was
   `IntoIter<SocketAddr>`. Fixed by passing `&str` (formatted
   `"host:port"`) directly to `TcpStream::connect`.

3. **Unused imports** — `sccp.rs` imported `BerDecoder`/`BerEncoder` but
   never used them (encoding is done via raw byte manipulation).
   Removed the import line.

## Cargo.toml

```toml
[package]
name = "ss7_tracker"
version = "1.0.0"
edition = "2021"

[dependencies]
clap = { version = "4", features = ["derive"] }
serde = { version = "1", features = ["derive"] }
serde_json = "1"
hex = "0.4"
```
