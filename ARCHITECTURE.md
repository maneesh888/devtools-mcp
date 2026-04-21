# DevTools MCP Architecture

## Overview

DevTools MCP is a cross-platform development tooling server that provides build, test, and deployment automation for AI agents via the Model Context Protocol (MCP).

## Design Principles

1. **Platform Independence**: Each platform (iOS, Android, Web, Server) is isolated in its own driver
2. **Consistent Interface**: All platforms implement the `PlatformDriver` base class
3. **Environment-Driven**: Configuration via `DEVTOOLS_<PLATFORM>_<SETTING>` env vars
4. **Incremental Implementation**: Platforms can be added/completed independently
5. **Zero Cross-Contamination**: iOS-specific code (Xcode, demo, localization) stays in iOS module

## Project Structure

```
devtools-mcp/
├── README.md              # Overview and quick start
├── SETUP.md               # Detailed setup guide
├── ROADMAP.md             # Implementation status
├── PLATFORMS.md           # Platform-specific guides
├── ARCHITECTURE.md        # This file
├── pyproject.toml         # Package config
├── .gitignore
│
├── src/devtools_mcp/
│   ├── __init__.py
│   ├── server.py          # MCP tool registry (FastMCP)
│   │
│   ├── platforms/         # Platform drivers
│   │   ├── __init__.py
│   │   ├── base.py        # PlatformDriver interface + BuildResult
│   │   ├── ios.py         # ✅ iOS driver (xcodebuild, simctl)
│   │   ├── android.py     # 🚧 Android driver (gradle, adb) [stub]
│   │   ├── web.py         # 🚧 Web driver (Playwright, build) [stub]
│   │   └── server.py      # 🚧 Server driver (Docker, API test) [stub]
│   │
│   ├── audit/             # Code quality checks
│   │   ├── __init__.py
│   │   ├── core.py        # Audit orchestration
│   │   ├── design_system_audit.py
│   │   ├── swift_hygiene_audit.py
│   │   └── file_metadata_audit.py
│   │
│   ├── localization/      # iOS xcstrings tooling (available, not exposed)
│   │   ├── __init__.py
│   │   ├── xcstrings.py
│   │   ├── auditor.py
│   │   ├── migrator.py
│   │   └── scripts/
│   │
│   ├── review/            # LLM-powered code review (iOS)
│   │   └── reviewer.py
│   │
│   ├── xcode_control.py   # iOS-specific AppleScript automation
│   ├── demo.py            # iOS-specific demo VC switcher
│   └── shared/            # Shared utilities
│
├── tests/                 # Unit tests
│   ├── test_build_parsing.py
│   ├── test_xcstrings_io.py
│   └── ...
│
└── hooks/                 # Git hooks
    └── pre-commit         # iOS pre-commit hook
```

## Platform Driver Interface

All platform drivers inherit from `PlatformDriver` (in `platforms/base.py`):

```python
class PlatformDriver(ABC):
    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Return human-readable platform name."""
        pass

    @abstractmethod
    def build(self, **kwargs) -> BuildResult:
        """Build the project. Returns BuildResult with errors/warnings."""
        pass

    def list_devices(self) -> list[dict]:
        """List available devices/simulators/emulators (optional)."""
        return []

    def run_cmd(self, cmd: list[str], timeout: int = 300) -> tuple[int, str, str]:
        """Execute shell command. Returns (rc, stdout, stderr)."""
        # ...implementation...
```

### BuildResult

Standardized build output structure:

```python
@dataclass
class BuildResult:
    success: bool
    errors: list[BuildError]
    warnings: list[BuildError]
    build_log_tail: str = ""
```

### BuildError

Individual error/warning with source location:

```python
@dataclass
class BuildError:
    file: str | None
    line: int | None
    column: int | None
    message: str
```

## MCP Tool Registration

Tools are registered in `server.py` using FastMCP:

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("devtools-mcp")

@mcp.tool()
def ios_build(...) -> str:
    """Build iOS project..."""
    result = ios.build(...)
    return json.dumps(result.to_dict(), indent=2)
```

## Environment Variables

Consistent naming: `DEVTOOLS_<PLATFORM>_<SETTING>`

Examples:
- `DEVTOOLS_IOS_PROJECT` — Path to .xcodeproj
- `DEVTOOLS_IOS_SCHEME` — Xcode scheme name
- `DEVTOOLS_ANDROID_PROJECT` — Path to Android project root
- `DEVTOOLS_WEB_PROJECT` — Path to web project root

Platform drivers read these in their module-level defaults.

## Code Quality Audits

Audit framework supports multiple checks:

```python
audit_changed_files(
    project_path="/path/to/project",
    checks=["design_system", "swift_hygiene", "file_metadata"],
    base_ref="master",  # or None for uncommitted changes
)
```

Each audit returns:
```python
{
    "category": "swift_hygiene",
    "code": "SH001",
    "severity": "warning",
    "line": 42,
    "message": "print() statement found",
    "suggested_fix": "Remove debug print or use proper logging"
}
```

## Adding a New Platform

1. **Create driver**: `src/devtools_mcp/platforms/<platform>.py`
   - Inherit from `PlatformDriver`
   - Implement `build()` at minimum
   - Add environment variable defaults

2. **Register tools**: Update `server.py`
   - Import the driver
   - Add `@mcp.tool()` functions wrapping driver methods

3. **Add tests**: `tests/test_<platform>.py`

4. **Document**: Update `PLATFORMS.md` and `ROADMAP.md`

See `platforms/ios.py` for a complete reference.

## Current Implementation Status

| Platform | Driver | Tools | Audit | Tests | Docs |
|----------|--------|-------|-------|-------|------|
| iOS      | ✅     | ✅    | ✅    | ✅    | ✅   |
| Android  | 🚧     | 🚧    | 🚧    | 🚧    | ✅   |
| Web      | 🚧     | 🚧    | 🚧    | 🚧    | ✅   |
| Server   | 🚧     | 🚧    | 🚧    | 🚧    | ✅   |

**Legend**: ✅ Complete | 🚧 Planned (stub exists) | ❌ Not started

## Dependencies

- **Core**: `mcp[cli]>=1.0.0` (Model Context Protocol)
- **Dev**: `pytest>=8.0` (testing)
- **Runtime**: Python 3.12+

Platform-specific dependencies (not in package requirements):
- **iOS**: Xcode, command-line tools
- **Android**: Android SDK, Gradle
- **Web**: Node.js, Playwright/Cypress
- **Server**: Docker (optional), platform-specific runtimes

---

*Clean architecture. Add platforms incrementally. Ship it.*
