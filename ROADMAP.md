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
- [x] `demo_set_launch_vc` / `demo_get_launch_vc` — VC switching
- [x] Pre-commit git hook

### Infrastructure
- [x] Platform driver architecture
- [x] Build result parsing framework
- [x] Error extraction and formatting
- [x] Localization tooling (xcstrings read/write)

## 📋 Planned

### Android Platform
- [ ] `android_build` — Gradle build with error parsing
- [ ] `android_list_emulators` — List AVDs
- [ ] `android_run_app` — Launch on emulator/device
- [ ] `android_stop_app` — Kill running app
- [ ] `android_install_apk` — Install APK
- [ ] Code quality audits (Kotlin/Java hygiene, Android Lint)
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

*Incremental implementation: iOS complete → Android → Web → Server*
