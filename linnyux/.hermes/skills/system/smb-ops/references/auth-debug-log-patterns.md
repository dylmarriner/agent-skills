# Auth Debug Log Patterns

## Reading Samba auth failure logs

When auth fails, enable log level 3, reproduce, then check the log for the mapped user:

### Pattern: Username map misdirection
```
check_sam_security: Couldn't find user 'admin' in passdb.
Authentication for user [kubuntux] -> [admin] FAILED with error NT_STATUS_NO_SUCH_USER
mapped to [WORKGROUP]\[admin]
```
This means: client sent `kubuntux`, but the username map (`admin = kubuntux` — backwards!) mapped it to `admin`, and `admin` doesn't exist in passdb.

**Fix**: Change the smbusers entry from `admin = kubuntux` to `kubuntux = admin`.

### Pattern: Correct auth (success)
```
echo "exit" | smbclient "//127.0.0.1/videos" -U kubuntux%admin
Try "help" to get a list of possible commands.
```
No auth error = success. The `Try "help"` prompt means you're connected.

### Pattern: Wrong password
`NT_STATUS_LOGON_FAILURE` — clear bad-password signal. Check `pdbedit -L -v` for `Bad password count`.

### Pattern: Guest blocked by valid users
```
tree connect failed: NT_STATUS_ACCESS_DENIED
```
With `map to guest = Bad User` + `guest ok = no` + `valid users = kubuntux`, guest connections get this. Client must authenticate.

## Quick test commands
```bash
# Guest test
echo "exit" | smbclient "//<ip>/<share>" -N 2>&1

# Auth test with inline password
echo "exit" | smbclient "//<ip>/<share>" -U <user>%<pass> 2>&1

# List shares as guest
smbclient -L //<ip> -N 2>&1
```
