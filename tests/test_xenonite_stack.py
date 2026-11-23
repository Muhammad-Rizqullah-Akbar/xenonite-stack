# -*- coding: utf-8 -*-
"""Comprehensive unit test suite for Xenonite 4-Layer Stack."""

from __future__ import annotations

import json
import tempfile
import unittest
import uuid
from pathlib import Path

from xenonite_stack.cli.installer import (
    HOOK_GUARD_KEY,
    HOOK_SESSION_KEY,
    MCP_SERVER_KEY,
    install_antigravity,
    uninstall_antigravity,
)
from xenonite_stack.cli.verifier import run_verify
from xenonite_stack.config import XenoniteSettings
from xenonite_stack.hooks.pre_tool_guard import evaluate_tool_call
from xenonite_stack.hooks.session_start import evaluate_hook
from xenonite_stack.mcp import (
    layer1_memory,
    layer3_code_intel,
    layer4_execution,
)


def _make_sqlite_settings(db_path: Path) -> XenoniteSettings:
    base = XenoniteSettings.load()
    return XenoniteSettings(
        **{
            **base.__dict__,
            "memory_backend": "sqlite",
            "sqlite_path": db_path,
        }
    )


class TestLayer1SQLiteMemory(unittest.TestCase):
    def test_remember_search_progress_and_list(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cfg = _make_sqlite_settings(Path(tmp) / "mem.db")

            res = layer1_memory.remember_context(
                project="alpha-api",
                title="Rate Limiter Contract",
                content="Use token bucket stored in Redis with 100 req/min burst.",
                domain="architecture",
                tags=["redis", "ratelimit"],
                files=["src/ratelimit.py"],
                settings=cfg,
            )
            self.assertIn("Saved memory [sqlite-fts5]", res)

            prog = layer1_memory.update_project_progress(
                project="alpha-api",
                feature="Auth Middleware",
                status="ready",
                note="Implemented JWT rotation and unit tests.",
                files=["src/auth.py"],
                settings=cfg,
            )
            self.assertIn("Saved memory [sqlite-fts5]", prog)

            found = layer1_memory.search_memory("token bucket Redis", project="alpha-api", settings=cfg)
            self.assertIn("Rate Limiter Contract", found)

            projects = layer1_memory.list_indexed_projects(settings=cfg)
            self.assertIn("alpha-api", projects)
            self.assertIn("architecture", projects)
            self.assertIn("progress", projects)


class TestLayer3CodeIntelligence(unittest.TestCase):
    def test_structure_outline_blast_radius_callers_and_snippets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "node_modules").mkdir()
            (root / "node_modules" / "ignored.js").write_text("export const x = 1;\n", encoding="utf-8")

            core_file = root / "core_service.py"
            core_file.write_text(
                "class CoreService:\n"
                "    def compute_score(self, x):\n"
                "        return x * 2\n",
                encoding="utf-8",
            )
            consumer_file = root / "handler.py"
            consumer_file.write_text(
                "from core_service import CoreService\n"
                "def handle():\n"
                "    return CoreService().compute_score(21)\n",
                encoding="utf-8",
            )

            tree = layer3_code_intel.get_project_structure(str(root), max_depth=3)
            self.assertIn("core_service.py", tree)
            self.assertNotIn("node_modules", tree)

            outline = layer3_code_intel.get_code_outline(str(core_file))
            self.assertIn("class CoreService:", outline)
            self.assertIn("def compute_score", outline)

            blast = layer3_code_intel.analyze_blast_radius(str(core_file), str(root))
            self.assertIn("handler.py", blast)

            callers = layer3_code_intel.analyze_function_callers("compute_score", str(root))
            self.assertIn("handler.py", callers)

            rg_out = layer3_code_intel.ripgrep_search("compute_score", str(root))
            self.assertIn("compute_score", rg_out)

            snippets = layer3_code_intel.read_targeted_snippets(
                [
                    {"file_path": str(core_file), "start_line": 1, "end_line": 3, "label": "core"},
                    {"file_path": str(consumer_file), "start_line": 2, "end_line": 3, "label": "handler"},
                ]
            )
            self.assertIn("return x * 2", snippets)
            self.assertIn("compute_score(21)", snippets)


class TestLayer4AtomicExecution(unittest.TestCase):
    def test_multi_patch_chained_and_rollback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            file_a = root / "a.py"
            file_b = root / "b.py"
            file_a.write_text("VALUE = 1\nNAME = 'old'\n", encoding="utf-8")
            file_b.write_text("FLAG = False\n", encoding="utf-8")

            # Chained patches on file_a + simultaneous patch on file_b
            res = layer4_execution.apply_multi_patch(
                [
                    {"path": str(file_a), "target": "VALUE = 1", "replacement": "VALUE = 2"},
                    {"path": str(file_a), "target": "NAME = 'old'", "replacement": "NAME = 'new'"},
                    {"path": str(file_b), "target": "FLAG = False", "replacement": "FLAG = True"},
                ]
            )
            self.assertIn("ATOMIC MULTI-PATCH SUCCESS", res)
            self.assertEqual(file_a.read_text(encoding="utf-8"), "VALUE = 2\nNAME = 'new'\n")
            self.assertEqual(file_b.read_text(encoding="utf-8"), "FLAG = True\n")

            # Pre-flight rollback when second patch target is missing
            fail = layer4_execution.apply_multi_patch(
                [
                    {"path": str(file_a), "target": "VALUE = 2", "replacement": "VALUE = 999"},
                    {"path": str(file_b), "target": "NON_EXISTENT", "replacement": "X"},
                ]
            )
            self.assertIn("Failed [Rollback]", fail)
            self.assertIn("VALUE = 2", file_a.read_text(encoding="utf-8"))

    def test_big_o_atlas(self) -> None:
        self.assertIn("Bitmask", layer4_execution.get_big_o_recommendation("permissions"))
        self.assertIn("not found", layer4_execution.get_big_o_recommendation("unknown_key"))


class TestHooksAndInstaller(unittest.TestCase):
    def test_session_and_pre_invocation_hooks(self) -> None:
        start = evaluate_hook({"conversationId": "c1"})
        self.assertIn("systemMessage", start["injectSteps"][0])

        pre = evaluate_hook({"conversationId": "c1", "invocationNum": 2})
        self.assertIn("ephemeralMessage", pre["injectSteps"][0])

    def test_pre_tool_guard_decisions(self) -> None:
        cid = f"unit-test-guard-{uuid.uuid4().hex}"
        deny_scan = evaluate_tool_call(
            {"conversationId": cid, "stepIdx": 1, "toolCall": {"name": "run_command", "args": {"CommandLine": "grep -rn secret ."}}}
        )
        self.assertEqual(deny_scan["decision"], "deny")

        allow_first_read = evaluate_tool_call(
            {"conversationId": cid, "stepIdx": 5, "toolCall": {"name": "read_file", "args": {"Path": "/tmp/a.py"}}}
        )
        self.assertEqual(allow_first_read["decision"], "allow")

        deny_second_read = evaluate_tool_call(
            {"conversationId": cid, "stepIdx": 6, "toolCall": {"name": "read_file", "args": {"Path": "/tmp/b.py"}}}
        )
        self.assertEqual(deny_second_read["decision"], "deny")

        allow_skill = evaluate_tool_call(
            {"conversationId": cid, "stepIdx": 7, "toolCall": {"name": "read_file", "args": {"Path": "/tmp/skills/SKILL.md"}}}
        )
        self.assertEqual(allow_skill["decision"], "allow")

    def test_non_destructive_install_verify_and_uninstall(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cfg_dir = Path(tmp)
            # Pre-existing unrelated MCP server must be preserved!
            (cfg_dir / "mcp_config.json").write_text(
                json.dumps({"mcpServers": {"custom-other-mcp": {"command": "node"}}}),
                encoding="utf-8",
            )

            rc = install_antigravity(config_dir=cfg_dir, persona="standard")
            self.assertEqual(rc, 0)

            mcp_data = json.loads((cfg_dir / "mcp_config.json").read_text(encoding="utf-8"))
            self.assertIn("custom-other-mcp", mcp_data["mcpServers"])
            self.assertIn(MCP_SERVER_KEY, mcp_data["mcpServers"])

            hooks_data = json.loads((cfg_dir / "hooks.json").read_text(encoding="utf-8"))
            self.assertIn(HOOK_SESSION_KEY, hooks_data)
            self.assertIn(HOOK_GUARD_KEY, hooks_data)

            self.assertEqual(run_verify(mode="all", config_dir=cfg_dir), 0)

            rc_un = uninstall_antigravity(config_dir=cfg_dir)
            self.assertEqual(rc_un, 0)

            mcp_after = json.loads((cfg_dir / "mcp_config.json").read_text(encoding="utf-8"))
            self.assertIn("custom-other-mcp", mcp_after["mcpServers"])
            self.assertNotIn(MCP_SERVER_KEY, mcp_after["mcpServers"])


if __name__ == "__main__":
    unittest.main()
