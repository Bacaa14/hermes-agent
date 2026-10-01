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
