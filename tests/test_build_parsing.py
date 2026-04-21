"""Tests for iOS build output parsing."""

import pytest

from devtools_mcp.platforms.base import BuildError, BuildResult
from devtools_mcp.platforms.ios import IOSDriver


class TestParseBuildOutput:
    """Tests for IOSDriver._parse_build_output()."""

    def test_parses_swift_error(self):
        output = (
            "/path/to/MyView.swift:42:10: error: cannot find 'foo' in scope\n"
        )
        errors, warnings = IOSDriver._parse_build_output(output)
        assert len(errors) == 1
        assert errors[0].file == "/path/to/MyView.swift"
        assert errors[0].line == 42
        assert errors[0].column == 10
        assert "foo" in errors[0].message

    def test_parses_warning(self):
        output = (
            "/path/to/File.swift:10:5: warning: unused variable 'x'\n"
        )
        errors, warnings = IOSDriver._parse_build_output(output)
        assert len(errors) == 0
        assert len(warnings) == 1
        assert warnings[0].line == 10

    def test_parses_linker_error(self):
        output = "ld: error: undefined symbol _main\n"
        errors, warnings = IOSDriver._parse_build_output(output)
        assert len(errors) == 1
        assert "Linker error" in errors[0].message
        assert errors[0].file is None

    def test_deduplicates_errors_by_message(self):
        output = (
            "/a.swift:1:1: error: same message\n"
            "error: same message\n"
        )
        errors, _ = IOSDriver._parse_build_output(output)
        # Both have "same message" but should only appear once in summary errors
        # The first one is file-level, second is build summary
        assert len(errors) == 1

    def test_deduplicates_warnings_by_location(self):
        output = (
            "/a.swift:10:5: warning: unused var\n"
            "/a.swift:10:5: warning: unused var\n"
        )
        _, warnings = IOSDriver._parse_build_output(output)
        assert len(warnings) == 1

    def test_empty_output(self):
        errors, warnings = IOSDriver._parse_build_output("")
        assert len(errors) == 0
        assert len(warnings) == 0

    def test_clean_build_output(self):
        output = "** BUILD SUCCEEDED **\n"
        errors, warnings = IOSDriver._parse_build_output(output)
        assert len(errors) == 0
        assert len(warnings) == 0


class TestBuildResult:
    """Tests for BuildResult serialization."""

    def test_to_dict_structure(self):
        result = BuildResult(
            success=True,
            errors=[],
            warnings=[],
            build_log_tail="BUILD SUCCEEDED",
        )
        d = result.to_dict()
        assert d["success"] is True
        assert d["error_count"] == 0
        assert d["warning_count"] == 0
        assert "BUILD SUCCEEDED" in d["build_log_tail"]

    def test_short_path_strips_derived_data(self):
        path = "/Users/maneesh/Library/Developer/Xcode/DerivedData/something/MyFile.swift"
        assert BuildResult._short_path(path) == "MyFile.swift"

    def test_short_path_strips_project_prefix(self):
        path = "/some/root/MyApp/MyApp/Revamp/Views/MyView.swift"
        assert BuildResult._short_path(path) == "MyApp/Revamp/Views/MyView.swift"

    def test_short_path_none(self):
        assert BuildResult._short_path(None) is None

    def test_grouped_warnings(self):
        warnings = [
            BuildError(file="/a.swift", line=1, column=1, message="same warning"),
            BuildError(file="/b.swift", line=2, column=1, message="same warning"),
            BuildError(file="/c.swift", line=3, column=1, message="different warning"),
        ]
        result = BuildResult(success=True, warnings=warnings)
        grouped = result._grouped_warnings()
        assert len(grouped) == 2
        # Find the "same warning" group
        same = [g for g in grouped if g["message"] == "same warning"][0]
        assert same["count"] == 2
        assert "example_locations" in same
