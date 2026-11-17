# Independent verification of recovered WPA/WEP keys

The cracker produces candidates; these derivations decide whether a candidate is a finding.
Implement them yourself, cross-check the vectors against an independent implementation, and
report `verified` only on a successful recomputation.

## Derivations (IEEE 802.11-2020)

```
PMK    = PBKDF2(HMAC-SHA1, passphrase, SSID, 4096, 256)                      # 32 octets
PMKID  = HMAC-SHA1(PMK, "PMK Name" || AA || SPA)[0:16]
PTK    = PRF-512(PMK, "Pairwise key expansion",
                 min(AA,SPA) || max(AA,SPA) || min(ANonce,SNonce) || max(ANonce,SNonce))
         PTK = KCK[16] || KEK[16] || TK[16] || MIC[16]
PTK(SHA-256 AKMs) = KDF-HMAC-SHA256(PMK, "Pairwise key expansion", <same input>, bits)
         KDF(K,A,B,len) = HMAC-SHA256(K, A || 0x00 || B || i) for i = 1.. , truncated
         384 bits -> 48-octet PTK (CCMP-128), 512 bits -> GCMP-256/SHA-384 suites
```

The min/max ordering is why swapping the nonces or the MAC pair must NOT change the PTK - a
crypto test asserting inequality there asserts the opposite of the spec.

## MIC algorithms - try all, name the match

| MIC | Selected by | KCK from |
| --- | --- | --- |
| `HMAC-SHA1(KCK, EAPOL)[0:16]` | original PSK/WPA2 AKMs | PRF-512 (SHA-1) |
| `HMAC-MD5(KCK, EAPOL)[0:16]` | WPA1 / TKIP, key descriptor version 1 | PRF-512 (SHA-1) |
| `AES-128-CMAC(KCK, EAPOL)` | SHA-256 AKMs (6/19/20 and AKM-defined) | KDF-HMAC-SHA256, 48-octet PTK |

A 22000 hash line does not record the AKM, so compute the MIC under every (algorithm x KDF)
combination and report which matched (`EAPOL MIC match (aes-128-cmac/sha256-kdf)`). A primitive
missing on the host (pycryptodome for CMAC) is reported as **unavailable**, never as a mismatch
- conflating the two writes off a real key.

## hc22000 / EAPOL-Key frame offsets

```
WPA*01*PMKID*MAC_AP*MAC_CLIENT*ESSID***MESSAGEPAIR
WPA*02*MIC*MAC_AP*MAC_CLIENT*ESSID*NONCE_AP*EAPOL_CLIENT*MESSAGEPAIR
```

- 9 fields, `*`-separated; **no SNONCE field** - the client nonce is inside the EAPOL blob.
- MACs are colon-less hex in the hash line; ESSID is hex-encoded.
- EAPOL-Key frame layout (802.11-2020 Fig. 12-30): 802.1X header(4) descriptor type(1)
  key info(2) key length(2) replay(8) **Key Nonce(32, offset 17)** key IV(16) key RSC(8)
  key ID(8) **MIC(16, offset 81)** key data length(2) key data. Offset 81 holds for every key
  descriptor version, which is also where hccapx/22000 material keeps it.
- Zero the MIC field before computing the MIC over the frame; hashcat material usually arrives
  pre-zeroed and zeroing twice is harmless.
- The message-pair bitmask decides usability: `000` M1+M2 (challenge), `010` M2+M3; `001` M1+M4
  and `101` M3+M4 store a **zeroed NONCE_CLIENT** and need nonce-error-correction, so no
  passphrase can be verified against them. Validate structure first (frame long enough to hold
  a MIC), then report the zeroed-nonce case with its own reason.
- Validate every field on parse (MIC 16, ANONCE 32, MAC shape, hex decodability, minimum EAPOL
  length) and **skip** lines that fail: rejecting bad material at the parse boundary also keeps
  it away from the cracking engine.

## WEP

Verify by decrypting a captured data frame with the candidate key (RC4 with the 24-bit IV) and
recomputing the CRC-32 ICV over the plaintext payload; a key that does not reproduce the ICV is
not verified even if `aircrack-ng` printed `KEY FOUND`. Try `-z` (PTW) first, then `-n 64` /
`-n 128`.

## Vector discipline

- PBKDF2-HMAC-SHA1, `P="password" S="salt" c=4096 dkLen=20` ->
  `4b007901b765489abead49d926f721d065a429c1` (RFC 6070).
- AES-128-CMAC, empty message, key `2b7e151628aed2a6abf7158809cf4f3c` ->
  `bb1d6929e95937287fa37d129b756746` (NIST SP 800-38B D.1 example 1).
- Before shipping any vector, compute it with an independent implementation and keep only the
  ones that agree; a plausible-looking hex string from memory is worse than no test.

## What is not verifiable (say so, don't fake it)

- **SAE (WPA3-Personal) only:** no offline dictionary attack exists against a correct SAE
  exchange. Applicable paths are WPS, transition-mode downgrade, or client-side work. Do not
  spend cracking time; do not ship an "SAE attack".
- **PMF required:** clients ignore deauthentication, so handshake capture becomes passive-only;
  PMKID still applies.
- **Enterprise (802.1X):** the PSK path does not apply - evil-twin/EAP downgrade and RADIUS
  configuration review are the topic, not PSK recovery.
- A **captured** PMKID/EAPOL is not a compromise: score it on the possibility of offline attack
  and label it captured, not cracked.
