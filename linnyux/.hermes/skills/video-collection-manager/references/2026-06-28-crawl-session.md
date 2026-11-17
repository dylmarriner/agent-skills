# Session-specific crawl reference — June 28, 2026

## Performer List (full crawl target)
Lana Rhoades, Lauren Phillips, Angela White, Alanna Pow, Kendra Sunderland,
Blake Blossom, Blondie Fesser, Karma RX, Violet Myers, Mia Malkova, Mia Melano,
Nicole Doshi, Sharon Lee, Lena Paul, Payton Preslee, Sophie Dee, Lexi,
Sky Bri, Kali Roses, Ava Nicks, Natasha Nice, Vivian Taylor, Alexis, Emily,
Rissa, Aleksa Mink, Faith, Camila Castillo, Bubblebratz, Riley, TruKait

Excluded: Steven (meme content)

## Target Sites
- eporner.com (primary, tag pages + pornstar pages)
- pimpbunny.com
- xhamster.com
- xxbrits.com
- porntn.com
- borntobefuck.com
- spankbang.com
- motherless.com (zero results for all performers)

## Crawl Results (other sites batch)
| Site | URLs |
|------|------|
| xhamster.com | 76 |
| spankbang.com | 61 |
| porntn.com | 28 |
| pimpbunny.com | 22 |
| borntobefuck.com | 5 |
| xxbrits.com | 2 |
| general web | 2 |
| motherless.com | 0 |
| **Total** | **196** |

## Dedup Results (this session)
1. **Exact MD5 dupes:** 14 removed (~7GB)
2. **RisqueCore <400MB:** 175 removed (~7.3GB) — kept only 10
3. **Trash files:** 8 removed (368MB)
   - Rick Astley rickroll (32MB)
   - 4 teaser/preview clips (<20s or <360p)
   - 3 garbage encodes (144p, 240p, 270p)
   - 1 corrupt file (4MB claiming 27min)
4. **Corrupt stub:** borntobefuck_30673.mp4 (3MB partial)
5. **Final count:** 549 → 351 MP4s, 205GB → 189GB

## Quality Thresholds
- RisqueCore: keep >400MB only
- Height <480: remove (144p, 240p, 360p, 270x480)
- Duration <20s: remove
- File <5MB + duration >60s: remove (corrupt)
- 404x720 / 406x720: NORMAL eporner vertical POV — keep

## Confirmed Working Commands
```
# Fast size-based dedup scan
cd /mnt/storage/videos
find . -name '*.mp4' -printf '%s\t%f\n' | sort -t$'\t' -k1,1n

# Full integrity scan sample
ffprobe -v error -select_streams v:0 -show_entries stream=width,height,duration -of json {file}

# Quick file count
ls *.mp4 | wc -l

# Total size
du -sh
```
