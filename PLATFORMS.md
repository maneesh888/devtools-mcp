# Platform-Specific Guides

This document provides detailed guides for each supported platform.

## iOS ✅ (Available Now)

### Prerequisites
- macOS with Xcode installed
- Command-line tools configured: `xcode-select --install`
- At least one iOS Simulator created

### Environment Setup

```bash
export DEVTOOLS_IOS_PROJECT="/path/to/YourApp.xcodeproj"
export DEVTOOLS_IOS_SCHEME="YourScheme"
export DEVTOOLS_IOS_CONFIGURATION="Debug"
export DEVTOOLS_IOS_SIMULATOR="iPhone 17 Pro"
```

### Available Tools

#### Build & Run
- **`ios_build`** — Build project, parse errors, optionally auto-run
  - Returns structured JSON with errors, warnings, build log
  - On success, triggers Xcode run (unless `run_after=False`)
  
- **`ios_list_simulators`** — List all simulators with UDID and state

- **`ios_simulator_screenshot`** — Capture current simulator screen to a PNG artifact

- **`ios_simulator_logs`** — Return a bounded simulator log tail with optional predicate filtering

- **`xcode_run_app`** — Send Cmd+R to Xcode (starts debugging session)

- **`xcode_stop_app`** — Send Cmd+. to Xcode (stops debugging)

#### Code Quality
- **`audit_changed_files`** — Pre-commit audit with parallel build
  - Swift hygiene (print, try!, fatalError, TODO)
  - Design system (hardcoded colors, system fonts)
  - File metadata (AI headers, copyright)

### Pre-Commit Hook

```bash
# From your iOS project root
ln -sf /path/to/devtools-mcp/hooks/pre-commit .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

---

## Android ✅ (Available Now)

### Prerequisites
- Android Studio installed
- Android SDK configured
- `ANDROID_HOME` or `ANDROID_SDK_ROOT` set
- At least one AVD created
- Gradle wrapper available in the Android project root

### Environment Setup

```bash
export DEVTOOLS_ANDROID_PROJECT="/path/to/android-project"
export DEVTOOLS_ANDROID_MODULE="app"
export DEVTOOLS_ANDROID_BUILD_VARIANT="debug"
export DEVTOOLS_ANDROID_EMULATOR="Pixel_7_API_34"
export DEVTOOLS_ANDROID_SDK_ROOT="$HOME/Library/Android/sdk"
```

### Available Tools

#### Build & Run

- **`android_build`** — Gradle build with error parsing
  - Parses Kotlin, Java, resource, and Gradle failure output
  - Returns structured JSON with errors, warnings, and build log tail

- **`android_list_emulators`** — List available AVDs

- **`android_list_devices`** — List connected adb devices

- **`android_start_emulator`** — Boot a configured AVD

- **`android_install_apk`** — Install APK to device/emulator

- **`android_run_app`** — Launch app on emulator/device

- **`android_stop_app`** — Kill running app process

#### Testing & Code Quality

- **`android_test`** — Run unit or instrumented tests and parse JUnit XML reports

- **`android_lint`** — Run Android Lint checks

- **`audit_kotlin_hygiene`** — Flag `println`, `!!`, and TODO/FIXME markers in Kotlin files

### Not Yet Available

- **`android_logcat`** — Filtered logcat output
- ProGuard/R8 integration

---

## Web 🚧 (Planned)

### Prerequisites (When Implemented)
- Node.js installed (or appropriate runtime)
- Project dependencies installed
- Playwright or Cypress configured (for testing)

### Planned Tools

#### Build & Deploy
- **`web_build`** — Run build command (Vite/Next.js/etc.)
- **`web_preview`** — Start local preview server
- **`web_deploy`** — Deploy to Vercel/Netlify/custom

#### Testing
- **`web_test`** — Run Playwright/Cypress tests
- **`web_lighthouse`** — Performance audit with Lighthouse
- **`web_bundle_analyze`** — Analyze bundle size

---

## Server 🚧 (Planned)

### Prerequisites (When Implemented)
- Runtime environment configured (Node/Python/Go/etc.)
- Docker installed (if using container tools)
- SSH keys configured (if using SSH deployment)

### Planned Tools

#### Testing
- **`server_test_api`** — Test REST/GraphQL endpoints
- **`server_health_check`** — Run health check suite

#### Docker
- **`docker_build`** — Build container image
- **`docker_run`** — Run container locally
- **`docker_compose_up`** — Start multi-service stack
- **`docker_compose_down`** — Stop services

#### Deployment
- **`deploy_ssh`** — SSH-based deployment
- **`deploy_rollback`** — Rollback to previous version

---

## Contributing New Platforms

To add a new platform:

1. Create `src/devtools_mcp/platforms/<platform>.py`
2. Implement the `PlatformDriver` interface from `base.py`
3. Add tools to `server.py` following the existing pattern
4. Update this guide with platform-specific docs
5. Add tests in `tests/test_<platform>.py`

See `platforms/ios.py` for a complete reference implementation.
