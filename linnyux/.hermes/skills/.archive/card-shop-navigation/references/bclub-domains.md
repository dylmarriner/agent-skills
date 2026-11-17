# BriansClub Domain Reference

## Primary Domains

| Domain | Status | Notes |
|--------|--------|-------|
| bclub.tk | Alive (DNS flaky on system resolvers, resolves on 8.8.8.8) | CNAME -> bclub.tk.cdn.cloudflare.net. IPs: 104.20.27.245, 172.66.152.79 |
| bclub.la | Best from headless browser | Served actual login page and CVV2 |
| bclub.cm | Alive but Cloudflare wall | Same backend |
| bclub.zip | Alive | Curl got through |
| bclub.lol | Cloudflare wall | - |
| bclub.mobi | Cloudflare wall | - |

## DNS Resolution

```
dig @8.8.8.8 bclub.tk  # Always works
```

If system resolver fails (ERR_NAME_NOT_RESOLVED):
```bash
curl --resolve "bclub.tk:443:104.20.27.245" https://bclub.tk/
```

## Login Endpoint

```
https://bclub.la/login2/
```

## Sections

| Section | Path |
|---------|------|
| CVV2 | /cvv/ |
| Dumps | /dumps/ (use nav) |
| Fullz | /fullz/ (use nav) |
| Orders | /orders/ (use nav) |
| Cart | /cart/ (use nav) |

## Notes

- Login page title: "Welcome!" — body: "PLEASE SIGN IN"
- Dashboard title: "Welcome" — shows balance and crab rating
- CVV2 page title: "CVV Search"
- Session timeout is short (minutes)
- Onion mirror: briansclcfyc5oe34hgxnn3akr4hzshy3edpwxsilvbsojp2gwxr57qd.onion
