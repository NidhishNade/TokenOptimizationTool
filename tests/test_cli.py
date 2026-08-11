"""Tests for the command-line interface.

We call ``cli.main()`` directly with argument lists and capture its output,
which is faster and more reliable than spawning a real subprocess.
"""

import pytest

from optimizer import cli


def test_optimize_file(tmp_path, capsys):
    f = tmp_path / "prompt.txt"
    f.write_text("Please summarize this.   Please summarize this.", encoding="utf-8")

    exit_code = cli.main([str(f)])
    out = capsys.readouterr()

    assert exit_code == 0
    assert "summarize" in out.out          # optimized text on stdout
    assert "Saved" in out.err              # report on stderr


def test_measure_only(tmp_path, capsys):
    f = tmp_path / "p.txt"
    f.write_text("Hello world, this is a test.", encoding="utf-8")

    exit_code = cli.main([str(f), "--measure-only"])
    out = capsys.readouterr()

    assert exit_code == 0
    assert "tokens" in out.out


def test_output_file_is_written(tmp_path):
    src = tmp_path / "in.txt"
    src.write_text("Please please summarize. Please please summarize.", encoding="utf-8")
    dest = tmp_path / "out.txt"

    exit_code = cli.main([str(src), "--output", str(dest)])

    assert exit_code == 0
    assert dest.exists()
    # The saved text should be shorter than the original.
    assert len(dest.read_text(encoding="utf-8")) < len(src.read_text(encoding="utf-8"))


def test_missing_file_errors():
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["does_not_exist.txt"])
    assert excinfo.value.code == 2


def test_empty_input_errors(tmp_path, capsys):
    f = tmp_path / "empty.txt"
    f.write_text("   \n  ", encoding="utf-8")

    exit_code = cli.main([str(f)])
    err = capsys.readouterr().err

    assert exit_code == 2
    assert "empty" in err.lower()


def test_aggressive_flag_changes_output(tmp_path, capsys):
    f = tmp_path / "p.txt"
    f.write_text("Please review the documentation because you are busy.", encoding="utf-8")

    cli.main([str(f), "--aggressive"])
    aggressive_out = capsys.readouterr().out

    # Aggressive shorthand should turn "documentation" into "docs".
    assert "docs" in aggressive_out.lower()


def test_advise_reports_repeated_block(tmp_path, capsys):
    block = "Follow the full company style guide and cite every source you use."
    f = tmp_path / "p.txt"
    f.write_text(f"{block}\n\nDo task one.\n\n{block}", encoding="utf-8")

    cli.main([str(f), "--advise"])
    err = capsys.readouterr().err

    assert "Structural suggestions" in err
    assert "appears" in err
