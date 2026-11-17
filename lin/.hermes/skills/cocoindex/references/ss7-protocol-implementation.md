# SS7 Protocol Implementation Notes

Extracted from conversation code analysis — real SS7/MAP/TCAP/SCCP encoding patterns.

## Protocol Stack (bottom-up)

```
M3UA (RFC 4666) — SIGTRAN transport over TCP
  ↓
SCCP (ITU-T Q.713) — routing + Global Title addressing
  ↓
TCAP (ITU-T Q.773) — transaction management (Begin/End/Continue/Abort)
  ↓
MAP (3GPP TS 29.002) — mobile network operations
```

## BER Encoding (ASN.1 X.690)

All upper layers use BER TLV encoding. Key primitives:

| Tag | Type | Encoding |
|-----|------|----------|
| 0x02 | INTEGER | Signed big-endian, length-prefixed |
| 0x04 | OCTET STRING | Raw bytes, length-prefixed |
| 0x05 | NULL | 0x05 0x00 |
| 0x30 | SEQUENCE (constructed) | Tag | 0x20, length, children |
| 0xA1-0xA4 | Context-specific (constructed) | Application-class tags for Invoke/ReturnResult/ReturnError/Reject |

Length encoding: short form (<128 bytes = single byte), long form (>=128 = 0x80|count + count bytes), indefinite (0x80 0x00).

## Key MAP Operations

| Code | Name | Purpose |
|------|------|---------|
| 0x31 (49) | AnyTimeInterrogation (ATI) | Subscriber location + state, no alert |
| 0x2D (45) | SendRoutingInfo (SRI) | Get MSC/VLR for MSISDN |
| 0x3A (58) | SendRoutingInfoForSM | Get SMS delivery MSC/SGSN |
| 0x41 (65) | ForwardShortMessage | Deliver SM to recipient MSC |
| 0x34 (52) | ProvideRoamingNumber (PRN) | Get MSRN for call routing |
| 0x0C (12) | InsertSubscriberData (ISD) | Modify HLR subscriber profile |

## M3UA Message Flow

```
1. ASP_UP        → (client sends)
2. ASP_UP_ACK    ← (server responds)
3. ASP_ACTIVE    → (client sends)  
4. ASP_ACTIVE_ACK ← (server responds)
5. DATA          → (SCCP+TCAP+MAP payload)
6. DATA          ← (response)
```

## Important Encoding Details

- TBCD encoding: phone number digits packed 2-per-byte (low nibble first)
- SCCP UDT: message type 0x09, followed by called/calling party addresses with routing indicators
- TCAP Begin: tag 0x62 (Application 2, constructed), contains OTID (0x48) + components (0xA1-0xA4)
- TCAP End: tag 0x64 (Application 4, constructed), contains DTID (0x49)
- MAP Context tags: tags 0x80-0x9E are primitive, 0xA0-0xBE are constructed
- MSISDN in MAP: TBCD-encoded under context tag [0] (0x80 or 0xA0)

## Rust Implementation Requirements

```toml
[dependencies]
# For M3UA TCP transport: tokio (no special crate needed)
# BER encoding/decoding: implement directly — simple TLV
# CLI: clap with derive feature
```

No external ASN.1 crate is needed — the SS7 BER subset (IMPLICIT tagging, primitive types, constructed sequences) is straightforward to implement in ~300 lines of pure Rust. A full BER library isn't warranted since we only need ~6 tag types.

## Testing Strategy

- Unit test each protocol layer independently (BER -> TCAP -> SCCP -> M3UA -> MAP)
- Test against known-good byte sequences from Wireshark captures
- The TCAP component encoding/decoding round-trips are the most failure-prone area
