# DevTools MCP Roadmap

## ✅ Implemented

### iOS Platform
- [x] `ios_build` — xcodebuild orchestration with error parsing
- [x] `ios_list_simulators` — List available simulators
- [x] `xcode_run_app` — AppleScript Cmd+R automation
- [x] `xcode_stop_app` — AppleScript Cmd+. automation
- [x] `audit_changed_files` — Pre-commit audit framework
  - [x] Design system audit (colors, fonts)
  - [x] Swift hygiene audit (print, try!, fatalError)
  - [x] File metadata audit (AI headers, copyright)
  - [x] Localization audit (available, not exposed)
- [x] Pre-commit git hook

### Android Platform
- [x] `android_build` — Gradle build with Kotlin, Java, resource, and Gradle failure parsing
- [x] `android_list_emulators` — List available AVDs
- [x] `android_list_devices` — List connected adb devices
- [x] `android_start_emulator` — Boot a configured AVD
- [x] `android_install_apk` — Install APK on device/emulator
- [x] `android_run_app` — Launch app on device/emulator
- [x] `android_stop_app` — Force-stop app on device/emulator
- [x] `android_test` — Run unit or instrumented tests and parse JUnit XML reports
- [x] `android_lint` — Run Android Lint and parse lint XML reports
- [x] `audit_kotlin_hygiene` — Check Kotlin for `println`, `!!`, and TODO/FIXME markers

### Infrastructure
- [x] Platform driver architecture
- [x] Build result parsing framework
- [x] Error extraction and formatting
- [x] Localization tooling (xcstrings read/write)

## 📋 Planned

### Android Improvements
- [ ] `android_logcat` — Filtered logcat output
- [ ] ProGuard/R8 integration

### Web Platform
- [ ] `web_build` — Vite/Next.js/React build orchestration
- [ ] `web_test` — Playwright/Cypress test runner
- [ ] `web_deploy` — Deployment automation (Vercel/Netlify/custom)
- [ ] `web_preview` — Local preview server management
- [ ] Browser automation helpers
- [ ] Lighthouse performance auditing
- [ ] Bundle size analysis

### Server Platform
- [ ] `server_test` — API endpoint testing (REST/GraphQL)
- [ ] `docker_build` — Container image building
- [ ] `docker_run` — Container orchestration
- [ ] `docker_compose` — Multi-service management
- [ ] `deploy_ssh` — SSH-based deployment
- [ ] Health check runners
- [ ] Log parsing and error extraction
- [ ] Database migration helpers

## 🔮 Future Enhancements

### Cross-Platform
- [ ] Unified workspace (mobile + web + server in one project)
- [ ] Shared code quality rules
- [ ] Multi-platform build orchestration
- [ ] Dependency graph analysis

### CI/CD Integration
- [ ] GitHub Actions helper tools
- [ ] GitLab CI integration
- [ ] Jenkins pipeline generation
- [ ] Build artifact management

### Testing & Quality
- [ ] Test coverage reporting
- [ ] Performance regression detection
- [ ] Security vulnerability scanning
- [ ] Dependency update automation

### Deployment
- [ ] Multi-environment management (dev/staging/prod)
- [ ] Rollback automation
- [ ] Blue-green deployment support
- [ ] Canary release helpers

### Monitoring & Observability
- [ ] Log aggregation and parsing
- [ ] Error tracking integration (Sentry/Rollbar)
- [ ] APM integration (New Relic/DataDog)
- [ ] Crash log analysis (iOS/Android)

---

*Incremental implementation: iOS + Android available → Web → Server*
