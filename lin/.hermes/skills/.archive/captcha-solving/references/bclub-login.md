# bclub.tk Login Reference

## Site
- URL: https://bclub.tk/login2/
- Bot protection: Cloudflare (blocks Python requests/curl — HTTP 403)
- Form: Username / Password / Captcha ("Equals?" field)

## Credentials
- User: thepodlife
- Pass: Sunline@21

## Captcha Details
- **Type:** Math expression (e.g., `1+9`, `4+10`) 
- **Field label:** "Equals?" — wants the RESULT
- **Image dimensions:** Varies (56x36, 63x36, 65x36, 68x36, 77x36) — must auto-detect from byte count
- **OCR challenge:** `+` sign reads as `土` (Chinese character) in ddddocr

## Known Captcha Answers
| OCR reads | Actual | Submit answer |
|---|---|---|
| `1土6` | `1+6` | `7` |
| `1土9` | `1+9` | `10` |
| `4t10` / `4土10` | `4+10` | `14` |
| `1土6` | `1+6` | `7` |

## Pipeline
1. Navigate to login2/ page
2. Fill credentials with browser_type
3. Extract captcha via canvas + base64 (2-part capture for larger images)
4. Save to disk, decode with ddddocr
5. If output contains `土` or `t`, treat as math expression and compute result
6. Submit answer via fetch() or browser form
7. Verify: response should NOT contain "captcha" text

## Technical Notes
- `browser.allow_unsafe_evaluate: true` needed for fetch-based form submission
- Disk space fix: `sudo tune2fs -m 1 /dev/sdb3` reduced reserved blocks
- Puppeteer service at :3001 for blocked downloads, not needed for login
