# Hilt + KSP Compatibility Reference

## Symptom

```
[ksp] InjectProcessingStep was unable to process
'SomeViewModel(...,error.NonExistentClass,...)' because
'error.NonExistentClass' could not be resolved.
```

The Hilt annotation processor can't resolve one of your constructor-parameter types during KSP. The Kotlin compilation itself succeeds (no `.kt:` errors), but KSP fails on the Hilt validation step.

## Root Cause

**Hilt version does not fully support the Kotlin version's KSP.** Hilt 2.51.x was released before Kotlin 2.0.0 shipped, so its KSP processor doesn't correctly resolve types from `@HiltViewModel` constructors that reference Android-specific qualifiers like `@ApplicationContext`.

## How to Diagnose: Pre-Existing vs Your Change

Before chasing a fix, verify the build was ever working:

```bash
git stash           # Remove your changes
rm -rf app/build    # Clean build artifacts
./gradlew assembleDebug   # Build original code
# Same error → pre-existing issue
# Different error or success → your change caused it
git stash pop       # Restore your changes
```

## Compatibility Matrix

| Hilt | Kotlin | KSP | Status |
|------|--------|-----|--------|
| 2.51.1 | 2.0.0 | 2.0.0-1.0.22 | ❌ `error.NonExistentClass` with `@HiltViewModel` |
| 2.52 | 2.0.0 | 2.0.0-1.0.24 | ❌ Same issue |
| 2.53.1 | 2.0.0 | 2.0.0-1.0.24 | ❌ Same issue |
| 2.54+ | 2.0.0+ | matching | ✅ Likely fixed (check release notes) |

## Workarounds

### 1. Upgrade Hilt (if available)
```toml
# gradle/libs.versions.toml
hilt = "2.53.1"  # or latest
ksp = "2.0.0-1.0.24"  # matching Kotlin 2.0.0
```

### 2. Remove `@HiltViewModel`, use manual factory
Replace `@HiltViewModel` with a regular `ViewModelProvider.Factory` in the composable.

### 3. Bump Kotlin version
If possible, upgrade to Kotlin 2.1+ where KSP/Hilt compatibility is more stable.

## References
- https://github.com/google/dagger/issues?q=NonExistentClass
- https://kotlinlang.org/docs/ksp.html
