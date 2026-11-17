# UUP Dump download details

## Build UUID for Win11 25H2 amd64 English US
- Build: 26200.8968 (Release Preview)
- UUID: 6b4cc4c9-525e-4904-9ac2-3cfbc0bce3da
- Edition codes: core, professional

## Edition page URL
`https://uupdump.net/download.php?id=6b4cc4c9-525e-4904-9ac2-3cfbc0bce3da&pack=en-us&edition=core;professional`

## API format for get.php
`https://uupdump.net/get.php?id=<UUID>&pack=<lang>&edition=<edition1>;<edition2>&aria2=2`

The `aria2=2` parameter returns the aria2 script content directly.
Semicolons between editions must be URL-encoded as `%3B`.
