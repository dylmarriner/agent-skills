# Native Android (Kotlin/Gradle) Build Troubleshooting

## Gradle Wrapper Without Gradle Binary

When `gradle` is not installed, create the wrapper manually:

```bash
# 1. Download the wrapper jar
curl -sL "https://raw.githubusercontent.com/gradle/gradle/v8.11.1/gradle/wrapper/gradle-wrapper.jar" \
  -o gradle/wrapper/gradle-wrapper.jar

# 2. Create gradle-wrapper.properties
mkdir -p gradle/wrapper
cat > gradle/wrapper/gradle-wrapper.properties << 'EOF'
distributionBase=GRADLE_USER_HOME
distributionPath=wrapper/dists
distributionUrl=https\://services.gradle.org/distributions/gradle-8.11.1-bin.zip
networkTimeout=10000
validateDistributionUrl=true
zipStoreBase=GRADLE_USER_HOME
zipStorePath=wrapper/dists
EOF

# 3. Create gradlew script (use the standard Gradle wrapper script from gradle.org)
# 4. chmod +x gradlew
```

**Pitfall**: The gradle-wrapper.jar is ~43KB and is a binary file — plain-text download may corrupt it. Use the raw.githubusercontent.com URL above which serves the binary correctly.

## WebRTC Dependency Not Resolving

`org.webrtc:google-webrtc:1.0.32006` is no longer available on Maven Central or Google's Maven repo.

**Fix**: Replace with `com.dafruits:webrtc:123.0.0` from Maven Central.

In `gradle/libs.versions.toml`:
```toml
[versions]
webrtc = "123.0.0"

[libraries]
webrtc = { group = "com.dafruits", name = "webrtc", version.ref = "webrtc" }
```

The `org.webrtc.*` import paths remain the same since `com.dafruits:webrtc` packages under the same namespace.

## kotlinx.serialization 1.7.x API Changes

`kotlinx.serialization:1.7.0+` removed `putJsonObject` and `putJsonArray` extension functions on `JsonObjectBuilder`.

**Before (1.6.x):**
```kotlin
buildJsonObject {
    putJsonObject("result") {
        putJsonArray("items") { add("a"); add("b") }
    }
}
```

**After (1.7.x):**
```kotlin
buildJsonObject {
    put("result", buildJsonObject {
        put("items", buildJsonArray { add(JsonPrimitive("a")); add(JsonPrimitive("b")) })
    })
}
```

Also note: `JsonArrayBuilder.add(String)` was removed — use `add(JsonPrimitive("string"))` explicitly.

## WebRTC M123 API Differences vs Newer Builds

The `com.dafruits:webrtc:123.0.0` library is based on WebRTC M123 (Chrome 123 era). Key API differences from newer builds:

| Feature | M123 API | Newer API |
|---------|----------|-----------|
| `PeerConnectionObserver` | Interface (no constructor) | Abstract class |
| ICE transport policy | `iceTransportsType` field on `RTCConfiguration` | `iceTransportPolicy` or removed |
| TLS cert policy | Not configurable | `tlsCertPolicy` field |
| DTLS/SRTP | Always enabled | `enableDtlsSrtp` flag |
| Data channel | Enabled by default | `enableRtpDataChannel` flag |
| ICE connection callback | `onIceConnectionChange(state)` | `onIceConnectionState(state)` |
| ICE gathering callback | `onIceGatheringChange(state)` | `onIceGatheringState(state)` |
| `DataChannel.label` | Method `label()` | Property `label` |
| `MediaStream.label` | Property `id` (inherited) | Property `label` |
| RTC stats `lastDataReceivedMs` | Field name | `lastReceivingTimestampMs` |
| `MediaCodec.PRIORITY_REALTIME` | Constant exists | May be removed in API 35 |

**Fix approach:** Use the M123 API names since that's what's compiled into the library. Check the actual `.class` files or jars in `~/.gradle/caches/` if uncertain.

## Missing Resource Files

If `AndroidManifest.xml` references `@mipmap/ic_launcher` but no mipmap resources exist:

**Option 1:** Reference an existing drawable instead:
```xml
android:icon="@drawable/ic_notification"
android:roundIcon="@drawable/ic_notification"
```

**Option 2:** Create adaptive icon resources (requires multiple density directories).

## Installing Missing SDK Platforms

```bash
export ANDROID_HOME=/path/to/sdk
yes | $ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager "platforms;android-35" "build-tools;35.0.0"
```

Check installed platforms first:
```bash
ls $ANDROID_HOME/platforms/
```

## Iterative Build Fix Loop

For fixing Kotlin compilation errors without Android Studio:

```bash
export ANDROID_HOME=/path/to/sdk
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64

cd project/
./gradlew assembleDebug 2>&1 | grep '^e:'    # Just errors
```

The grep pattern `^e:` captures `e: file://...` error lines from Kotlin compiler output, ignoring warnings (`w:`).
