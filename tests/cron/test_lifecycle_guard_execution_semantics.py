"""Lifecycle recursion follows execution semantics, not path-shaped data."""

from cron.lifecycle_guard import contains_gateway_lifecycle_command_or_referenced_script as guard


def test_data_path_literal_is_not_scanned_as_a_script(tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    ledger.write_text('{"history": "hermes gateway restart"}\n', encoding="utf-8")

    python_line = f"ledger = Path('{ledger}')"

    assert guard(python_line, cwd=str(tmp_path)) is False


def test_direct_and_referenced_lifecycle_commands_remain_blocked(tmp_path):
    script = tmp_path / "restart.sh"
    script.write_text("#!/bin/sh\nhermes gateway restart\n", encoding="utf-8")

    assert guard("hermes gateway restart", cwd=str(tmp_path)) is True
    assert guard(f"bash {script}", cwd=str(tmp_path)) is True
    assert guard(f"cat <({script})", cwd=str(tmp_path)) is True
    assert guard(f"echo result=<({script})", cwd=str(tmp_path)) is True
    assert guard(f"echo `({script})`", cwd=str(tmp_path)) is True
    assert guard(f"if true; then (bash {script}); fi", cwd=str(tmp_path)) is True
    assert guard(f"{{ (bash {script}); }}", cwd=str(tmp_path)) is True
    assert guard(f"function f {{ (bash {script}); }}; f", cwd=str(tmp_path)) is True
    assert guard(f"subprocess.run('{script}')", cwd=str(tmp_path)) is True
    assert guard(f"subprocess.run(Path('{script}'))", cwd=str(tmp_path)) is True
    assert guard(f"subprocess.getoutput('{script}')", cwd=str(tmp_path)) is True
    assert guard(f"runpy.run_path('{script}')", cwd=str(tmp_path)) is True
    assert guard(f"asyncio.create_subprocess_exec('{script}')", cwd=str(tmp_path)) is True
    assert guard(f"os.posix_spawn(Path('{script}'))", cwd=str(tmp_path)) is True
    assert guard(f"os.startfile('{script}')", cwd=str(tmp_path)) is True
    assert guard(f"system('{script}')", cwd=str(tmp_path)) is True
    assert guard(f"sp.run('{script}')", cwd=str(tmp_path)) is True


def test_unknown_require_load_and_aliased_execution_calls_fail_closed(tmp_path):
    script = tmp_path / "restart.js"
    script.write_text("hermes gateway restart\n", encoding="utf-8")

    assert guard(f"node - <<'JS'\nrequire('{script}')\nJS", cwd=str(tmp_path)) is True
    assert guard(f"node - <<'JS'\nload('{script}')\nJS", cwd=str(tmp_path)) is True
    assert (
        guard(
            f"python3 - <<'PY'\nimport subprocess\ninvoke = subprocess.run\ninvoke(['node', '{script}'])\nPY",
            cwd=str(tmp_path),
        )
        is True
    )


def test_execution_calls_scan_only_executable_argv_positions(tmp_path):
    worker = tmp_path / "worker.py"
    ledger = tmp_path / "ledger.jsonl"
    ledger.write_text('{"history": "hermes gateway restart"}\n', encoding="utf-8")

    worker.write_text("print('safe')\n", encoding="utf-8")
    command = f"subprocess.run(['python3', '{worker}', Path('{ledger}')])"
    assert guard(command, cwd=str(tmp_path)) is False
    assert guard(f"runtime_config(Path('{ledger}'))", cwd=str(tmp_path)) is False

    worker.write_text("hermes gateway restart\n", encoding="utf-8")
    assert guard(command, cwd=str(tmp_path)) is True


def test_rebound_data_call_names_are_scanned_as_execution(tmp_path):
    script = tmp_path / "restart.sh"
    script.write_text("#!/bin/sh\nhermes gateway restart\n", encoding="utf-8")
    script.chmod(0o755)

    for name in ("Path", "PurePath", "PosixPath", "WindowsPath", "open"):
        command = f"import subprocess\n{name} = subprocess.run\n{name}('{script}')"
        assert guard(command, cwd=str(tmp_path)) is True


def test_multiline_and_keyword_execution_arguments_are_scanned(tmp_path):
    script = tmp_path / "restart.sh"
    script.write_text("#!/bin/sh\nhermes gateway restart\n", encoding="utf-8")
    script.chmod(0o755)

    multiline = (
        "python3 - <<'PY'\n"
        "import subprocess\n"
        "if True:\n"
        "    marker = 'complete suite'\n"
        "    subprocess.run(\n"
        f"        ['bash', '{script}']\n"
        "    )\n"
        "PY"
    )
    keyword = f"subprocess.run(args=['bash', '{script}'])"

    assert guard(multiline, cwd=str(tmp_path)) is True
    assert guard(keyword, cwd=str(tmp_path)) is True


def test_nested_scope_cannot_restore_rebound_execution_name(tmp_path):
    script = tmp_path / "restart.sh"
    script.write_text("#!/bin/sh\nhermes gateway restart\n", encoding="utf-8")
    script.chmod(0o755)
    command = (
        "import subprocess\n"
        "Path = subprocess.run\n"
        "def unused():\n"
        "    from pathlib import Path\n"
        f"Path('{script}')"
    )

    assert guard(command, cwd=str(tmp_path)) is True

    deferred = (
        "def invoke():\n"
        f"    Path('{script}')\n"
        "import subprocess\n"
        "Path = subprocess.run\n"
        "invoke()"
    )
    loop_target = f"import subprocess\nfor Path in [subprocess.run]:\n    Path('{script}')"
    attribute = (
        "import builtins, subprocess\n"
        "builtins.open = subprocess.run\n"
        f"builtins.open('{script}')"
    )
    conditional = (
        "import subprocess\n"
        "Path = subprocess.run\n"
        "for item in []:\n"
        "    from pathlib import Path\n"
        f"Path('{script}')"
    )

    for source in (deferred, loop_target, attribute, conditional):
        assert guard(source, cwd=str(tmp_path)) is True


def test_structurally_proven_data_call_aliases_remain_inert(tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    ledger.write_text('{"history": "hermes gateway restart"}\n', encoding="utf-8")
    commands = (
        f"import builtins\nbuiltins.open('{ledger}').read()",
        f"import io\nio.open('{ledger}').read()",
        f"import pathlib\nPath = pathlib.Path\nPath('{ledger}')",
        f"from pathlib import Path\nPath: type\nPath('{ledger}')",
    )

    for command in commands:
        assert guard(command, cwd=str(tmp_path)) is False


def test_execution_api_specific_keyword_path_is_scanned(tmp_path):
    script = tmp_path / "restart.py"
    script.write_text("import os\nos.system('hermes gateway restart')\n", encoding="utf-8")

    assert guard(f"runpy.run_path(path_name='{script}')", cwd=str(tmp_path)) is True
