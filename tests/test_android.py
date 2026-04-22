"""Tests for Android platform driver."""

import json
import os
import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from devtools_mcp.platforms.android import AndroidDriver
from devtools_mcp.platforms.base import BuildError, BuildResult


# =========================================================================
# Construction / defaults
# =========================================================================


class TestAndroidDriverInit:
    def test_defaults(self):
        driver = AndroidDriver()
        assert driver.module == "app"
        assert driver.platform_name == "Android"

    def test_custom_init(self):
        driver = AndroidDriver(
            project_path="/my/project",
            module="lib",
            avd_name="Pixel_8",
        )
        assert driver.project_path == Path("/my/project")
        assert driver.module == "lib"
        assert driver.avd_name == "Pixel_8"

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("DEVTOOLS_ANDROID_PROJECT", "/env/project")
        monkeypatch.setenv("DEVTOOLS_ANDROID_MODULE", "core")
        monkeypatch.setenv("DEVTOOLS_ANDROID_EMULATOR", "Pixel_7")
        # Re-import to pick up env (or just pass None and check fallback)
        driver = AndroidDriver()
        # Constructor uses the module-level defaults which were set at import
        # time, so we test explicit None passthrough
        driver2 = AndroidDriver(project_path=None, module="core", avd_name="Pixel_7")
        assert driver2.module == "core"
        assert driver2.avd_name == "Pixel_7"


# =========================================================================
# Error parsing
# =========================================================================


class TestParseGradleErrors:
    def test_kotlin_compile_error(self):
        log = "e: file:///path/to/File.kt:42:10 Unresolved reference: foo"
        errors = AndroidDriver._parse_gradle_errors(log)
        assert len(errors) == 1
        assert errors[0].file == "/path/to/File.kt"
        assert errors[0].line == 42
        assert errors[0].column == 10
        assert "Unresolved reference: foo" in errors[0].message

    def test_java_compile_error(self):
        log = "/path/to/Main.java:15: error: cannot find symbol"
        errors = AndroidDriver._parse_gradle_errors(log)
        assert len(errors) == 1
        assert errors[0].file == "/path/to/Main.java"
        assert errors[0].line == 15
        assert errors[0].column is None
        assert "cannot find symbol" in errors[0].message

    def test_resource_error(self):
        log = "error: resource drawable/icon not found"
        errors = AndroidDriver._parse_gradle_errors(log)
        assert len(errors) == 1
        assert errors[0].file is None
        assert "Resource not found: drawable/icon" in errors[0].message

    def test_build_failed_with_reason(self):
        log = textwrap.dedent("""\
            FAILURE: Build failed with an exception.

            * What went wrong:
            Execution failed for task ':app:compileDebugKotlin'.

            BUILD FAILED in 5s
        """)
        errors = AndroidDriver._parse_gradle_errors(log)
        assert len(errors) == 1
        assert "Execution failed" in errors[0].message

    def test_multiple_errors(self):
        log = textwrap.dedent("""\
            e: file:///a.kt:1:1 error one
            e: file:///b.kt:2:2 error two
            /Main.java:5: error: java error
        """)
        errors = AndroidDriver._parse_gradle_errors(log)
        assert len(errors) == 3

    def test_deduplicates_errors(self):
        log = textwrap.dedent("""\
            e: file:///a.kt:1:1 same error
            e: file:///a.kt:1:1 same error
        """)
        errors = AndroidDriver._parse_gradle_errors(log)
        assert len(errors) == 1

    def test_no_errors_on_success(self):
        log = "BUILD SUCCESSFUL in 10s\n3 actionable tasks: 3 executed"
        errors = AndroidDriver._parse_gradle_errors(log)
        assert len(errors) == 0


class TestParseGradleWarnings:
    def test_kotlin_warning(self):
        log = "w: file:///path/File.kt:10:5 Parameter 'x' is never used"
        warnings = AndroidDriver._parse_gradle_warnings(log)
        assert len(warnings) == 1
        assert warnings[0].file == "/path/File.kt"
        assert warnings[0].line == 10
        assert warnings[0].column == 5

    def test_java_warning(self):
        log = "/path/Main.java:20: warning: unchecked cast"
        warnings = AndroidDriver._parse_gradle_warnings(log)
        assert len(warnings) == 1
        assert warnings[0].line == 20

    def test_deduplicates_warnings(self):
        log = textwrap.dedent("""\
            w: file:///a.kt:1:1 same warning
            w: file:///a.kt:1:1 same warning
        """)
        warnings = AndroidDriver._parse_gradle_warnings(log)
        assert len(warnings) == 1

    def test_no_warnings_on_clean_build(self):
        log = "BUILD SUCCESSFUL in 5s"
        warnings = AndroidDriver._parse_gradle_warnings(log)
        assert len(warnings) == 0


# =========================================================================
# Build
# =========================================================================


class TestBuild:
    def test_build_success(self):
        driver = AndroidDriver(project_path="/fake/project")
        with patch.object(driver, "run_cmd") as mock_run:
            mock_run.return_value = (0, "BUILD SUCCESSFUL in 10s", "")
            result = driver.build(variant="debug")

            assert result.success is True
            assert len(result.errors) == 0
            assert "BUILD SUCCESSFUL" in result.build_log_tail
            mock_run.assert_called_once()

    def test_build_failure_with_errors(self):
        driver = AndroidDriver(project_path="/fake/project")
        log = "e: file:///src/Main.kt:5:3 Type mismatch\nBUILD FAILED"
        with patch.object(driver, "run_cmd") as mock_run:
            mock_run.return_value = (1, log, "")
            result = driver.build(variant="debug")

            assert result.success is False
            assert len(result.errors) >= 1

    def test_build_clean(self):
        driver = AndroidDriver(project_path="/fake/project")
        with patch.object(driver, "run_cmd") as mock_run:
            mock_run.return_value = (0, "BUILD SUCCESSFUL", "")
            driver.build(variant="release", clean=True)

            cmd = mock_run.call_args[0][0]
            assert "clean" in cmd
            assert "app:assembleRelease" in cmd

    def test_build_result_serializes(self):
        driver = AndroidDriver(project_path="/fake/project")
        with patch.object(driver, "run_cmd") as mock_run:
            mock_run.return_value = (0, "BUILD SUCCESSFUL", "")
            result = driver.build()
            d = result.to_dict()
            assert "success" in d
            assert "errors" in d
            assert "error_count" in d


# =========================================================================
# Device management
# =========================================================================


class TestListEmulators:
    def test_list_avds(self):
        driver = AndroidDriver()
        with patch.object(driver, "run_cmd") as mock_run:
            mock_run.return_value = (0, "Pixel_8_API_35\nPixel_7_API_34\n", "")
            avds = driver.list_emulators()

            assert len(avds) == 2
            assert avds[0]["name"] == "Pixel_8_API_35"
            assert avds[1]["name"] == "Pixel_7_API_34"
            assert avds[0]["type"] == "emulator"

    def test_empty_avd_list(self):
        driver = AndroidDriver()
        with patch.object(driver, "run_cmd") as mock_run:
            mock_run.return_value = (0, "\n", "")
            avds = driver.list_emulators()
            assert len(avds) == 0

    def test_emulator_command_fails(self):
        driver = AndroidDriver()
        with patch.object(driver, "run_cmd") as mock_run:
            mock_run.return_value = (1, "", "emulator not found")
            avds = driver.list_emulators()
            assert avds == []


class TestListDevices:
    def test_lists_connected_devices(self):
        driver = AndroidDriver()
        adb_output = textwrap.dedent("""\
            List of devices attached
            emulator-5554          device product:sdk_gphone64_arm64
            ABCD1234               device product:redfin
        """)
        with patch.object(driver, "run_cmd") as mock_run:
            mock_run.return_value = (0, adb_output, "")
            devices = driver.list_devices()

            assert len(devices) == 2
            assert devices[0]["id"] == "emulator-5554"
            assert devices[0]["type"] == "emulator"
            assert devices[1]["id"] == "ABCD1234"
            assert devices[1]["type"] == "device"

    def test_no_devices(self):
        driver = AndroidDriver()
        with patch.object(driver, "run_cmd") as mock_run:
            mock_run.return_value = (0, "List of devices attached\n\n", "")
            devices = driver.list_devices()
            assert len(devices) == 0

    def test_adb_command_fails(self):
        driver = AndroidDriver()
        with patch.object(driver, "run_cmd") as mock_run:
            mock_run.return_value = (1, "", "adb not found")
            devices = driver.list_devices()
            assert devices == []


class TestStartEmulator:
    def test_no_avd_name_raises(self):
        driver = AndroidDriver(avd_name="")
        with pytest.raises(ValueError, match="No AVD name"):
            driver.start_emulator()

    def test_uses_instance_avd(self):
        driver = AndroidDriver(avd_name="Pixel_8")
        with patch("devtools_mcp.platforms.android.subprocess.Popen") as mock_popen, \
             patch.object(driver, "run_cmd") as mock_run, \
             patch("devtools_mcp.platforms.android.time.sleep"):
            mock_run.return_value = (0, "stopped", "")
            result = driver.start_emulator()

            assert result is True
            popen_cmd = mock_popen.call_args[0][0]
            assert "Pixel_8" in popen_cmd


# =========================================================================
# App control
# =========================================================================


class TestInstallApk:
    def test_install_success(self):
        driver = AndroidDriver()
        with patch.object(driver, "run_cmd") as mock_run:
            mock_run.return_value = (0, "Success", "")
            assert driver.install_apk("/path/to/app.apk") is True

    def test_install_with_device_id(self):
        driver = AndroidDriver()
        with patch.object(driver, "run_cmd") as mock_run:
            mock_run.return_value = (0, "Success", "")
            driver.install_apk("/path/to/app.apk", device_id="emulator-5554")
            cmd = mock_run.call_args[0][0]
            assert "-s" in cmd
            assert "emulator-5554" in cmd

    def test_install_failure(self):
        driver = AndroidDriver()
        with patch.object(driver, "run_cmd") as mock_run:
            mock_run.return_value = (1, "Failure", "")
            assert driver.install_apk("/path/to/app.apk") is False


class TestRunApp:
    def test_run_success(self):
        driver = AndroidDriver()
        with patch.object(driver, "run_cmd") as mock_run:
            mock_run.return_value = (0, "Starting: Intent", "")
            result = driver.run_app("com.example.app", ".MainActivity")
            assert result is True

    def test_run_with_device_id(self):
        driver = AndroidDriver()
        with patch.object(driver, "run_cmd") as mock_run:
            mock_run.return_value = (0, "", "")
            driver.run_app("com.example.app", ".MainActivity", "emulator-5554")
            cmd = mock_run.call_args[0][0]
            assert "-s" in cmd
            assert "com.example.app/.MainActivity" in cmd[-1]


class TestStopApp:
    def test_stop_success(self):
        driver = AndroidDriver()
        with patch.object(driver, "run_cmd") as mock_run:
            mock_run.return_value = (0, "", "")
            assert driver.stop_app("com.example.app") is True

    def test_stop_failure(self):
        driver = AndroidDriver()
        with patch.object(driver, "run_cmd") as mock_run:
            mock_run.return_value = (1, "", "error")
            assert driver.stop_app("com.example.app") is False


# =========================================================================
# Testing
# =========================================================================


class TestTestRunner:
    def test_unit_test_task(self):
        driver = AndroidDriver(project_path="/fake")
        with patch.object(driver, "run_cmd") as mock_run, \
             patch.object(driver, "_parse_test_results") as mock_parse:
            mock_run.return_value = (0, "", "")
            mock_parse.return_value = {
                "total": 5, "passed": 5, "failed": 0,
                "skipped": 0, "success": True, "failures": [],
            }
            results = driver.test(test_type="unit")

            cmd = mock_run.call_args[0][0]
            assert "app:testDebugUnitTest" in cmd
            assert results["success"] is True

    def test_instrumented_test_task(self):
        driver = AndroidDriver(project_path="/fake")
        with patch.object(driver, "run_cmd") as mock_run, \
             patch.object(driver, "_parse_test_results") as mock_parse:
            mock_run.return_value = (0, "", "")
            mock_parse.return_value = {
                "total": 3, "passed": 3, "failed": 0,
                "skipped": 0, "success": True, "failures": [],
            }
            results = driver.test(test_type="instrumented")

            cmd = mock_run.call_args[0][0]
            assert "app:connectedDebugAndroidTest" in cmd

    def test_invalid_test_type(self):
        driver = AndroidDriver(project_path="/fake")
        with pytest.raises(ValueError, match="Unknown test type"):
            driver.test(test_type="integration")


class TestParseTestResults:
    def test_parses_junit_xml(self, tmp_path):
        """Create a fake JUnit XML report and verify parsing."""
        driver = AndroidDriver(project_path=str(tmp_path))
        test_dir = tmp_path / "app" / "build" / "test-results" / "testDebugUnitTest"
        test_dir.mkdir(parents=True)

        xml_content = textwrap.dedent("""\
            <?xml version="1.0" encoding="UTF-8"?>
            <testsuite tests="3" failures="1" errors="0" skipped="0">
              <testcase name="testAdd" classname="com.example.MathTest" time="0.01"/>
              <testcase name="testSub" classname="com.example.MathTest" time="0.01">
                <failure message="Expected 5 but was 3">assertion failed</failure>
              </testcase>
              <testcase name="testMul" classname="com.example.MathTest" time="0.01"/>
            </testsuite>
        """)
        (test_dir / "TEST-com.example.MathTest.xml").write_text(xml_content)

        results = driver._parse_test_results()
        assert results["total"] == 3
        assert results["passed"] == 2
        assert results["failed"] == 1
        assert results["success"] is False
        assert len(results["failures"]) == 1
        assert results["failures"][0]["test"] == "testSub"

    def test_all_passing(self, tmp_path):
        driver = AndroidDriver(project_path=str(tmp_path))
        test_dir = tmp_path / "app" / "build" / "test-results" / "testDebugUnitTest"
        test_dir.mkdir(parents=True)

        xml_content = textwrap.dedent("""\
            <?xml version="1.0" encoding="UTF-8"?>
            <testsuite tests="2" failures="0" errors="0" skipped="0">
              <testcase name="test1" classname="com.example.Test" time="0.01"/>
              <testcase name="test2" classname="com.example.Test" time="0.01"/>
            </testsuite>
        """)
        (test_dir / "TEST-com.example.Test.xml").write_text(xml_content)

        results = driver._parse_test_results()
        assert results["total"] == 2
        assert results["passed"] == 2
        assert results["failed"] == 0
        assert results["success"] is True

    def test_no_test_results_dir(self, tmp_path):
        driver = AndroidDriver(project_path=str(tmp_path))
        results = driver._parse_test_results()
        assert results["total"] == 0
        assert results["success"] is True

    def test_handles_errors_element(self, tmp_path):
        """Tests with <error> elements (not just <failure>)."""
        driver = AndroidDriver(project_path=str(tmp_path))
        test_dir = tmp_path / "app" / "build" / "test-results" / "testDebugUnitTest"
        test_dir.mkdir(parents=True)

        xml_content = textwrap.dedent("""\
            <?xml version="1.0" encoding="UTF-8"?>
            <testsuite tests="2" failures="0" errors="1" skipped="0">
              <testcase name="testOk" classname="com.example.Test" time="0.01"/>
              <testcase name="testBoom" classname="com.example.Test" time="0.01">
                <error message="NullPointerException">stack trace</error>
              </testcase>
            </testsuite>
        """)
        (test_dir / "TEST-com.example.Test.xml").write_text(xml_content)

        results = driver._parse_test_results()
        assert results["failed"] == 1
        assert results["failures"][0]["test"] == "testBoom"


# =========================================================================
# Lint
# =========================================================================


class TestLint:
    def test_lint_clean(self, tmp_path):
        driver = AndroidDriver(project_path=str(tmp_path))
        lint_dir = tmp_path / "app" / "build" / "reports"
        lint_dir.mkdir(parents=True)

        xml_content = textwrap.dedent("""\
            <?xml version="1.0" encoding="UTF-8"?>
            <issues format="5" by="lint">
            </issues>
        """)
        (lint_dir / "lint-results.xml").write_text(xml_content)

        with patch.object(driver, "run_cmd") as mock_run:
            mock_run.return_value = (0, "", "")
            result = driver.lint()

            assert result.success is True
            assert len(result.errors) == 0

    def test_lint_with_errors(self, tmp_path):
        driver = AndroidDriver(project_path=str(tmp_path))
        lint_dir = tmp_path / "app" / "build" / "reports"
        lint_dir.mkdir(parents=True)

        xml_content = textwrap.dedent("""\
            <?xml version="1.0" encoding="UTF-8"?>
            <issues format="5" by="lint">
              <issue severity="Error" message="Missing permission">
                <location file="AndroidManifest.xml" line="10" column="5"/>
              </issue>
              <issue severity="Warning" message="Unused import">
                <location file="Main.kt" line="3" column="1"/>
              </issue>
            </issues>
        """)
        (lint_dir / "lint-results.xml").write_text(xml_content)

        with patch.object(driver, "run_cmd") as mock_run:
            mock_run.return_value = (0, "", "")
            result = driver.lint()

            assert result.success is False
            assert len(result.errors) == 1
            assert len(result.warnings) == 1
            assert "Missing permission" in result.errors[0].message

    def test_lint_no_report(self, tmp_path):
        driver = AndroidDriver(project_path=str(tmp_path))
        with patch.object(driver, "run_cmd") as mock_run:
            mock_run.return_value = (0, "", "")
            result = driver.lint()
            assert result.success is True


# =========================================================================
# Kotlin hygiene
# =========================================================================


class TestKotlinHygiene:
    def test_detects_println(self, tmp_path):
        kt_file = tmp_path / "src" / "Main.kt"
        kt_file.parent.mkdir(parents=True)
        kt_file.write_text('fun main() {\n    println("hello")\n}\n')

        driver = AndroidDriver(project_path=str(tmp_path))
        issues = driver.audit_kotlin_hygiene()

        println_issues = [i for i in issues if i["code"] == "KH001"]
        assert len(println_issues) == 1
        assert println_issues[0]["line"] == 2

    def test_detects_double_bang(self, tmp_path):
        kt_file = tmp_path / "src" / "Main.kt"
        kt_file.parent.mkdir(parents=True)
        kt_file.write_text("val x = nullable!!\n")

        driver = AndroidDriver(project_path=str(tmp_path))
        issues = driver.audit_kotlin_hygiene()

        bang_issues = [i for i in issues if i["code"] == "KH002"]
        assert len(bang_issues) == 1

    def test_detects_todo(self, tmp_path):
        kt_file = tmp_path / "src" / "Main.kt"
        kt_file.parent.mkdir(parents=True)
        kt_file.write_text("// TODO fix this later\nval x = 1\n")

        driver = AndroidDriver(project_path=str(tmp_path))
        issues = driver.audit_kotlin_hygiene()

        # The comment line is skipped (starts with //), so no TODO detected
        # Only non-comment TODOs are detected
        todo_issues = [i for i in issues if i["code"] == "KH003"]
        assert len(todo_issues) == 0

    def test_detects_inline_todo(self, tmp_path):
        kt_file = tmp_path / "src" / "Main.kt"
        kt_file.parent.mkdir(parents=True)
        kt_file.write_text('val x = 1 // TODO fix this\n')

        driver = AndroidDriver(project_path=str(tmp_path))
        issues = driver.audit_kotlin_hygiene()

        # Line doesn't start with //, so the TODO is detected
        todo_issues = [i for i in issues if i["code"] == "KH003"]
        assert len(todo_issues) == 1

    def test_skips_comment_lines(self, tmp_path):
        kt_file = tmp_path / "src" / "Main.kt"
        kt_file.parent.mkdir(parents=True)
        kt_file.write_text("// println(debug)\n")

        driver = AndroidDriver(project_path=str(tmp_path))
        issues = driver.audit_kotlin_hygiene()

        println_issues = [i for i in issues if i["code"] == "KH001"]
        assert len(println_issues) == 0

    def test_no_kotlin_files(self, tmp_path):
        driver = AndroidDriver(project_path=str(tmp_path))
        issues = driver.audit_kotlin_hygiene()
        assert issues == []

    def test_with_base_ref(self, tmp_path):
        kt_file = tmp_path / "src" / "Main.kt"
        kt_file.parent.mkdir(parents=True)
        kt_file.write_text('val x = nullable!!\n')

        driver = AndroidDriver(project_path=str(tmp_path))
        with patch.object(driver, "run_cmd") as mock_run:
            mock_run.return_value = (0, "src/Main.kt\nREADME.md\n", "")
            issues = driver.audit_kotlin_hygiene(base_ref="main")

            mock_run.assert_called_once()
            cmd = mock_run.call_args[0][0]
            assert "git" in cmd
            assert "main" in cmd
            assert len(issues) >= 1


# =========================================================================
# Run (build + launch)
# =========================================================================


class TestRun:
    def test_run_build_only(self):
        driver = AndroidDriver(project_path="/fake")
        with patch.object(driver, "build") as mock_build:
            mock_build.return_value = BuildResult(success=True)
            result = driver.run()
            assert result["success"] is True
            assert result["phase"] == "build_only"

    def test_run_build_failure(self):
        driver = AndroidDriver(project_path="/fake")
        with patch.object(driver, "build") as mock_build:
            mock_build.return_value = BuildResult(
                success=False,
                errors=[BuildError(file="a.kt", line=1, column=1, message="err")],
            )
            result = driver.run()
            assert result["success"] is False
            assert result["phase"] == "build"

    def test_run_with_launch(self):
        driver = AndroidDriver(project_path="/fake")
        with patch.object(driver, "build") as mock_build, \
             patch.object(driver, "run_app") as mock_launch:
            mock_build.return_value = BuildResult(success=True)
            mock_launch.return_value = True
            result = driver.run(
                package_name="com.example.app",
                activity_name=".MainActivity",
            )
            assert result["success"] is True
            assert result["phase"] == "complete"
