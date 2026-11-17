### Embedded Postgres Library Fixes

If you encounter `error while loading shared libraries: libicui18n.so.60: cannot open shared object file`, it is due to an embedded binary requiring an older system library version.

1. **Check available versions:**
   ```bash
   find /usr/lib -name "libicui18n.so.*"
   ```
2. **Symlink Compatibility:** If you have version 70 or higher installed, you may be able to link to it:
   ```bash
   # Example: sudo ln -s /usr/lib/x86_64-linux-gnu/libicui18n.so.70 /usr/lib/x86_64-linux-gnu/libicui18n.so.60
   ```
   *Note: This is a workaround; verify the binary works after linking.*
3. **Compatibility Package:** Search your distribution package manager for `libicu60` or a compatibility package for the required version.
