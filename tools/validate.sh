#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
cache="${WFF_TOOLS_DIR:-.cache/wff}"
mkdir -p "$cache" build/reports/wff
fetch_tool() {
    local name="$1" checksum="$2" file="$cache/$1.jar"
    if [[ ! -f "$file" ]]; then
        curl --fail --location --retry 3 "https://github.com/google/watchface/releases/download/release/$name.jar" -o "$file"
    fi
    printf '%s  %s\n' "$checksum" "$file" | sha256sum --check --status
}
# Google's release tag is mutable. Fail closed if its artifacts change; review
# the upstream release and deliberately refresh hashes before updating tools.
fetch_tool wff-validator 28b244289ab748bb2b07017e9f3c06bb76bdf165d6fa55652a5dc64b852c3121
fetch_tool memory-footprint 6a5aa266821562d264859d09be6b771a509c478370fbc0c2336d4ed4c0ca5890
python3 tools/generate_watchface.py --check
python3 -m unittest discover -s tests -v
java -jar "$cache/wff-validator.jar" 2 app/src/main/res/raw/watchface.xml 2>&1 | tee build/reports/wff/schema.txt
# Some validator releases print failure but return exit status zero.
grep -q 'PASSED' build/reports/wff/schema.txt
! grep -q 'FAILED\|SEVERE' build/reports/wff/schema.txt
./gradlew :app:assembleDebug :app:bundleRelease :app:lint
python3 tools/check_packages.py
for package in app/build/outputs/apk/debug/app-debug.apk app/build/outputs/bundle/release/app-release.aab; do
    name="$(basename "$package")"
    java -jar "$cache/memory-footprint.jar" --watch-face "$package" --schema-version 2 \
        --ambient-limit-mb 10 --active-limit-mb 100 2>&1 | tee "build/reports/wff/$name-memory.txt"
    grep -q 'PASS' "build/reports/wff/$name-memory.txt"
    ! grep -q 'FAIL' "build/reports/wff/$name-memory.txt"
    java -jar "$cache/memory-footprint.jar" --watch-face "$package" --schema-version 2 --report \
        > "build/reports/wff/$name-memory.json"
done
