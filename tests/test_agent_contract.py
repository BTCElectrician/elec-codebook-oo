import argparse
import json
import re
import tomllib
from pathlib import Path

import pytest

from codebook_agent import __version__, cli
from codebook_agent.agent_contract import (
    CLI_CONTRACT_VERSION,
    CODE_MAP,
    COMMANDS,
    EXIT_CODES,
    OUTPUT_SCHEMAS,
)
from codebook_agent.cli import CAPABILITIES, build_parser, main

ROOT = Path(__file__).resolve().parents[1]


def _subcommand_names() -> set[str]:
    parser = build_parser()
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return set(action.choices)
    raise AssertionError("CLI parser has no subcommands")


def test_bare_invocation_is_a_safe_first_try(capsys):
    assert main([]) == 0
    captured = capsys.readouterr()
    assert "codebook agent --json" in captured.out
    assert "configure -> plan -> dry" in captured.out
    assert captured.err == ""


@pytest.mark.parametrize(
    "arguments",
    [
        ["--help"],
        ["help", "plan"],
        ["agent", "--help"],
        ["answer", "--help"],
        ["ask", "--help"],
        ["capabilities", "--help"],
        ["clean", "--help"],
        ["configure", "--help"],
        ["doctor", "--help"],
        ["dry", "--help"],
        ["export", "--help"],
        ["ingest", "--help"],
        ["plan", "--help"],
        ["query", "--help"],
        ["robot-docs", "--help"],
        ["robot-docs", "guide", "--help"],
        ["schema", "--help"],
        ["search", "--help"],
        ["smoke", "--help"],
    ],
)
def test_every_help_path_succeeds(arguments, capsys):
    assert main(arguments) == 0
    captured = capsys.readouterr()
    assert "usage:" in captured.out
    assert captured.err == ""


def test_parser_and_machine_command_catalog_have_the_same_surface():
    parser_commands = _subcommand_names() - {"capabilities"}
    contract_commands = {name.split()[0] for name in COMMANDS}
    assert parser_commands == contract_commands
    assert COMMANDS["caps"]["aliases"] == ["capabilities"]
    for details in COMMANDS.values():
        assert {
            "summary",
            "connections",
            "writes",
            "apply_required",
            "json",
            "example",
        } <= details.keys()


def test_capabilities_are_complete_and_versioned(capsys):
    assert main(["capabilities", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload == CAPABILITIES
    assert payload["cli_contract_version"] == CLI_CONTRACT_VERSION
    assert payload["package_version"] == __version__
    assert payload["commands"] == COMMANDS
    assert payload["exit_codes"] == EXIT_CODES
    assert payload["output_schemas"] == OUTPUT_SCHEMAS
    assert payload["environment"]["CODEBOOK_DATABASE_URL"]["printed"] is False
    assert payload["environment"]["OPENAI_API_KEY"]["printed"] is False


def test_agent_triage_is_deterministic_side_effect_free_json(capsys):
    assert main(["agent", "--json"]) == 0
    first = capsys.readouterr()
    assert main(["--robot-triage"]) == 0
    second = capsys.readouterr()

    assert first.err == second.err == ""
    assert first.out == second.out
    payload = json.loads(first.out)
    assert payload["safe_to_run"] is True
    assert payload["side_effects"] == {"connections": [], "writes": []}
    assert payload["entrypoints"]["change_map"] == "docs/CODEMAP.md"
    assert set(payload["interaction_contract"]["supported_intents"]) == {
        "understand",
        "explain",
        "change",
        "run",
        "verify",
    }
    assert payload["health"]["next_commands"]
    assert payload["recommended_next_actions"]


def test_machine_output_stays_parseable_when_a_typo_is_inferred(capsys):
    assert main(["capabilties", "--jsno"]) == 0
    captured = capsys.readouterr()
    assert json.loads(captured.out)["package"] == "elec-codebook-oo"
    assert "inferred command" in captured.err
    assert "inferred option" in captured.err


def test_unknown_intent_fails_with_a_next_action(capsys):
    assert main(["frobnicate"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "invalid choice" in captured.err
    assert "codebook help" in captured.err


def test_apply_is_never_inferred_from_a_typo(tmp_path, capsys):
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    marker = artifacts / "generated.txt"
    marker.write_text("generated", encoding="utf-8")

    assert main(["clean", "--artifacts", str(artifacts), "--aply"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "inferred option `--apply`" not in captured.err
    assert marker.exists()


def test_schema_discovery_is_deterministic(capsys):
    assert main(["schema", "--json"]) == 0
    first = capsys.readouterr()
    assert main(["schema", "--json"]) == 0
    second = capsys.readouterr()
    assert first == second
    assert json.loads(first.out) == {
        "contract_version": CLI_CONTRACT_VERSION,
        "schemas": OUTPUT_SCHEMAS,
    }
    assert "profile-proposal" in OUTPUT_SCHEMAS


def test_robot_guide_is_available_as_text_and_json(capsys):
    assert main(["robot-docs", "guide"]) == 0
    text_result = capsys.readouterr()
    assert "Read AGENTS.md and STATUS.md" in text_result.out
    assert "ingest --apply" in text_result.out

    assert main(["robot-docs", "gide", "--json"]) == 0
    json_result = capsys.readouterr()
    assert "inferred topic" in json_result.err
    assert "Hard boundaries" in json.loads(json_result.out)["guide"]


def test_ask_has_a_structured_mode(capsys):
    assert main(["ask", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["contract_version"] == CLI_CONTRACT_VERSION
    assert payload["profile"]["id"] == "generic-reference-template"
    assert payload["questions"]
    assert payload["next"].endswith("then run plan.")


def test_retrieval_and_answer_json_use_the_contract_envelope(
    monkeypatch,
    capsys,
):
    monkeypatch.setattr(cli, "_pgvector_search", lambda args: [])

    assert main(["search", "--query", "synthetic", "--json"]) == 0
    search = json.loads(capsys.readouterr().out)
    assert search == {
        "contract_version": CLI_CONTRACT_VERSION,
        "query": "synthetic",
        "results": [],
    }

    assert main(["answer", "--query", "synthetic", "--json"]) == 0
    answer = json.loads(capsys.readouterr().out)
    assert answer["contract_version"] == CLI_CONTRACT_VERSION
    assert answer["query"] == "synthetic"
    assert answer["mode"] == "extractive"
    assert answer["sources"] == []


def test_cleanup_is_preview_first_and_apply_gated(tmp_path, capsys):
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    marker = artifacts / "generated.txt"
    marker.write_text("generated", encoding="utf-8")

    assert main(["clean", "--artifacts", str(artifacts)]) == 0
    preview = json.loads(capsys.readouterr().out)
    assert preview["applied"] is False
    assert preview["writes"] == []
    assert marker.exists()

    assert main(["clean", "--artifacts", str(artifacts), "--apply"]) == 0
    applied = json.loads(capsys.readouterr().out)
    assert applied["applied"] is True
    assert applied["writes"] == [str(artifacts.resolve())]
    assert not artifacts.exists()


def test_output_has_no_terminal_control_sequences(monkeypatch, capsys):
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.setenv("CI", "1")
    monkeypatch.setenv("TERM", "dumb")
    assert main(["agent", "--json"]) == 0
    captured = capsys.readouterr()
    assert re.search(r"\x1b\[[0-9;]*[A-Za-z]", captured.out + captured.err) is None


def test_code_map_contract_paths_exist():
    for area in CODE_MAP.values():
        for relative_path in area["paths"]:
            assert (ROOT / relative_path).exists(), relative_path
        assert area["invariants"]


def test_cross_model_entrypoints_defer_to_canonical_authority():
    claude = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    gemini = (ROOT / "GEMINI.md").read_text(encoding="utf-8")
    copilot = (ROOT / ".github" / "copilot-instructions.md").read_text(encoding="utf-8")
    for text in (claude, gemini, copilot):
        assert "AGENTS.md" in text
        assert "CODEMAP.md" in text
    assert "@AGENTS.md" in claude


def test_public_front_door_links_agent_navigation():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for path in (
        "AGENTS.md",
        "STATUS.md",
        "docs/CODEMAP.md",
        "docs/AGENT_ONBOARDING.md",
    ):
        assert path in readme
    assert "make agent-json" in readme


def test_local_markdown_links_resolve():
    markdown_files = [
        ROOT / "README.md",
        ROOT / "AGENTS.md",
        ROOT / "CLAUDE.md",
        ROOT / "CONTRIBUTING.md",
        ROOT / "GEMINI.md",
        ROOT / "SECURITY.md",
        ROOT / "STATUS.md",
        *(ROOT / "docs").glob("*.md"),
    ]
    failures = []
    for markdown in markdown_files:
        text = markdown.read_text(encoding="utf-8")
        for raw_target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", text):
            target = raw_target.strip("<>").split("#", 1)[0]
            if not target or "://" in target or target.startswith("mailto:"):
                continue
            if not (markdown.parent / target).resolve().exists():
                failures.append(f"{markdown.relative_to(ROOT)} -> {raw_target}")
    assert failures == []


def test_makefile_exposes_agent_native_discovery_targets():
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    targets = {
        match.group(1)
        for match in re.finditer(r"^([a-z][a-z0-9-]*):(?:\\s|$)", makefile, re.MULTILINE)
    }
    assert {
        "agent-json",
        "caps-json",
        "configure",
        "doctor",
        "help",
        "robot-docs",
        "schemas-json",
        "test-agent",
    } <= targets


def test_package_version_has_one_public_value():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    status = (ROOT / "STATUS.md").read_text(encoding="utf-8")
    assert project["project"]["version"] == __version__
    assert f"Version {__version__}" in status
    assert f"version-{__version__}" in readme


def test_version_flag_reports_the_public_version(capsys):
    assert main(["--version"]) == 0
    assert capsys.readouterr().out.strip() == f"codebook {__version__}"
