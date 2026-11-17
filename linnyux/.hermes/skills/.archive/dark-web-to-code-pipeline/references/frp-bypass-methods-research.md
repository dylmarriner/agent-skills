# FRP Bypass Methods Research — Compiled Knowledge

## Source
Compiled from dark web crawls (608 known .onion addresses, 170 crawl cycles), surface web forums (XDA, Reddit), and community research.

## Categories by Chipset/Android Version

### Android 11-13
- TalkBack accessibility exploit (Volume Up+Down → TalkBack → Chrome → APK install)
- Emergency dialer codes (`*#0*#`, `*#12580*369#`, `*#2263#`, `*#9090#`, `*#7284#`, `*#0808#`, `*#9900#`)
- ADB intent manipulation (`am start -a android.intent.action.DIAL -d tel:{code}`)
- Accounts database modification (delete `/data/system/users/0/accounts.db`)
- Persist partition editing (mount /persist, clear FRP flag files)
- Bootloader unlock + TWRP recovery flash → ADB shell → clear FRP

### Android 14-15
- Updated TalkBack gesture timing and navigation paths
- Google Assistant voice commands ("open settings", "open chrome", "show account settings")
- Chrome URL navigation to bypass APK download sites
- Framework property patching (`ro.frp.pst`, `persist.sys.frp` properties)
- Qualcomm EDL mode (Firehose programmer → read/write FRP partition)
- Samsung AT command modem injection

### Android 15-16 (2026 Methods)
- Chrome `chrome://flags/#enable-adb` exploit to re-enable USB debugging
- NFC settings route bypass (open NFC settings from setup wizard)
- New Samsung engineering dialer codes: `*#08#`, `*#27663368378#`, `*#367635#`
- TalkBack 2026 gesture sequence (updated timing, Volume Up+Down sequence)
- Google Assistant voice shell commands for deeper navigation

## Tool Reference

| Tool | Targets | Type | Success |
|------|---------|------|---------|
| SamFw FRP Tool | Samsung | Free/Odin | 85% |
| Tenorshare 4uKey | All brands | Paid | 95% |
| Dr.Fone Unlock | All brands | Paid | 90% |
| TFT Unlock | MediaTek | Paid | 92% |
| BMB Unlock Tool | Oppo/Vivo/Realme | Paid | 88% |
| Pangu FRP Bypass | Samsung/Motorola | Free | 80% |

## Dark Web Sources
- Hidden Wiki (zqktlwiuavv...) — GSM/unlock resource aggregation
- Exploit Forum (exploitivzcm5...) — security research
- Various marketplaces — paid unlock tools
- Continuous crawler daemon: 170 cycles, 608 known onions
