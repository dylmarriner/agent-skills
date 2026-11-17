#!/bin/bash
# Quick verification script for Android development setup

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=== Android Development Setup Verification ==="
echo ""

errors=0
warnings=0

# Check Java
echo -n "Checking Java... "
if java -version 2>&1 | grep -q "17\|21\|22"; then
  echo -e "${GREEN}✓ ${NC}Java $(java -version 2>&1 | head -1 | cut -d'"' -f2)"
else
  echo -e "${YELLOW}⚠ ${NC}(Java found but version may be incorrect)"
  errors=$((errors+1))
fi

# Check JAVA_HOME
echo -n "Checking JAVA_HOME... "
if [ -n "$JAVA_HOME" ] && [ -f "$JAVA_HOME/bin/java" ]; then
  echo -e "${GREEN}✓ ${NC}$JAVA_HOME"
else
  echo -e "${RED}✗ ${NC}JAVA_HOME not set or invalid"
  errors=$((errors+1))
fi

# Check Android Studio
echo -n "Checking Android Studio... "
if [ -f "$HOME/android-studio/bin/studio.sh" ]; then
  echo -e "${GREEN}✓ ${NC}Found"
else
  echo -e "${RED}✗ ${NC}Not found"
  errors=$((errors+1))
fi

# Check ADB
echo -n "Checking ADB... "
if command -v adb &> /dev/null; then
  adb_version=$(adb version 2>&1 | head -1)
  echo -e "${GREEN}✓ ${NC}$adb_version"
else
  echo -e "${RED}✗ ${NC}Not found"
  errors=$((errors+1))
fi

# Check platform-tools
echo -n "Checking platform-tools... "
if [ -f "$ANDROID_HOME/platform-tools/adb" ] || [ -f "$HOME/android-studio/sdk/platform-tools/adb" ]; then
  echo -e "${GREEN}✓ ${NC}Found"
else
  echo -e "${RED}✗ ${NC}Not found"
  errors=$((errors+1))
fi

# Check SDK Manager
echo -n "Checking SDK Manager... "
if command -v sdkmanager &> /dev/null; then
  echo -e "${GREEN}✓ ${NC}Found"
else
  echo -e "${YELLOW}⚠ ${NC}(Could be installed but not in PATH)"
  warnings=$((warnings+1))
fi

# Check AVD Manager
echo -n "Checking AVD Manager... "
if command -v avdmanager &> /dev/null; then
  echo -e "${GREEN}✓ ${NC}Found"
else
  echo -e "${YELLOW}⚠ ${NC}(Could be installed but not in PATH)"
  warnings=$((warnings+1))
fi

# Check Emulator
echo -n "Checking Emulator... "
if command -v emulator &> /dev/null; then
  echo -e "${GREEN}✓ ${NC}Found"
else
  echo -e "${YELLOW}⚠ ${NC}(Could be installed but not in PATH)"
  warnings=$((warnings+1))
fi

# Check Java version compatibility
echo -n "Checking Java compatibility... "
java_version=$(java -version 2>&1 | head -1 | grep -oE '[0-9]+' | head -1)
if [ "$java_version" -ge 17 ]; then
  echo -e "${GREEN}✓ ${NC}Java $java_version is compatible"
else
  echo -e "${RED}✗ ${NC}Java $java_version is too old (need 17+)"
  errors=$((errors+1))
fi

# Check disk space
echo -n "Checking disk space... "
disk_free=$(df -h "$HOME" | tail -1 | awk '{print $4}')
disk_free_gb=$(echo "$disk_free" | grep -oE '[0-9]+')

if [ "$disk_free_gb" -ge 19 ]; then
  echo -e "${GREEN}✓ ${NC}${disk_free} available"
else
  echo -e "${YELLOW}⚠ ${NC}Low disk space (recommended: 19+ GB, available: $disk_free)"
  warnings=$((warnings+1))
fi

# Check installed platforms
echo -n "Checking installed platforms... "
platform_count=$(ls -d $ANDROID_HOME/platforms/android-* 2>/dev/null | wc -l)
if [ "$platform_count" -gt 0 ]; then
  echo -e "${GREEN}✓ ${NC}$platform_count platform(s) installed"
else
  echo -e "${YELLOW}⚠ ${NC}No platforms found (will need to download)"
  warnings=$((warnings+1))
fi

# Check installed system images
echo -n "Checking system images... "
image_count=$(ls -d $ANDROID_HOME/system-images/android-* 2>/dev/null | wc -l)
if [ "$image_count" -gt 0 ]; then
  echo -e "${GREEN}✓ ${NC}$image_count system image(s) available"
else
  echo -e "${YELLOW}⚠ ${NC}No system images found (will need to download)"
  warnings=$((warnings+1))
fi

# Summary
echo ""
echo "=== Summary ==="
echo "Errors: $errors | Warnings: $warnings"

if [ $errors -eq 0 ] && [ $warnings -eq 0 ]; then
  echo -e "${GREEN}All checks passed! Android development environment is ready.${NC}"
  exit 0
elif [ $errors -eq 0 ]; then
  echo -e "${YELLOW}Some warnings present. Setup is mostly ready.${NC}"
  exit 0
else
  echo -e "${RED}Setup has errors. See output above for details.${NC}"
  exit 1
fi
