"""Tests for `referee.sdk.AgentSdkReferee` with a fake client in place of the Claude CLI.

These tests check the SDK options from ADR 0002 and how SDK messages become
Referee events. They never start the real SDK.
"""
import asyncio

import pytest

sdk = pytest.importorskip("claude_agent_sdk")

from harness_fixtures import make_campaign, open_engine  # noqa: E402

from solo_roll.harness.campaign import CampaignPaths  # noqa: E402
from solo_roll.harness.referee.sdk import AgentSdkReferee, RefereeConfigError  # noqa: E402


class FakeClient:
    """Plays back SDK messages; runs engine tool handlers when a script asks."""

    def __init__(self, options, script, memory_files=()):
        self.options = options
        self.script = list(script)
        self.memory_files = list(memory_files)
        self.queries = []
        self.connected = False
        self.disconnected = False

    async def connect(self):
        self.connected = True

    async def get_context_usage(self):
        return {"totalTokens": 3700, "memoryFiles": self.memory_files}

    async def query(self, prompt):
        self.queries.append(prompt)

    async def receive_response(self):
        for item in self.script.pop(0):
            if callable(item):
                item = await item(self.options)
            yield item

    async def disconnect(self):
        self.disconnected = True


def delta(text):
    return sdk.StreamEvent(
        uuid="u", session_id="s", event={"type": "content_block_delta", "delta": {"type": "text_delta", "text": text}}
    )


def assistant(*blocks):
    return sdk.AssistantMessage(content=list(blocks), model="sonnet")


def tool_use(tool_id, name, tool_input):
    return assistant(sdk.ToolUseBlock(id=tool_id, name=name, input=tool_input))


def tool_result(tool_id, is_error=False, content="ok"):
    return sdk.UserMessage(content=[sdk.ToolResultBlock(tool_use_id=tool_id, content=content, is_error=is_error)])


def result(is_error=False):
    return sdk.ResultMessage(
        subtype="success", duration_ms=1, duration_api_ms=1, is_error=is_error, num_turns=1, session_id="s"
    )


def run_engine_tool(name, args):
    async def call(options):
        handler = next(t for t in options.mcp_servers["engine"]["tools"] if t.name == name).handler
        await handler(args)
        return None

    return call


def run_hook(tool_name, tool_input, tool_id):
    async def call(options):
        hook = options.hooks["PreToolUse"][0].hooks[0]
        await hook({"tool_name": tool_name, "tool_input": tool_input, "hook_event_name": "PreToolUse"}, tool_id, {})
        return None

    return call


@pytest.fixture(autouse=True)
def plain_mcp_server(monkeypatch):
    """Keep the engine tools readable: the SDK's in-process MCP server hides its handlers."""
    monkeypatch.setattr(
        "solo_roll.harness.referee.sdk.create_sdk_mcp_server",
        lambda name, tools: {"type": "sdk", "name": name, "tools": tools},
    )


@pytest.fixture
def paths(tmp_path):
    return CampaignPaths(make_campaign(tmp_path))


@pytest.fixture
def engine(paths):
    return open_engine(paths.root)


def make_referee(engine, paths, *turns, memory_files=()):
    clients = []

    def factory(options):
        clients.append(FakeClient(options, turns, memory_files))
        return clients[-1]

    return AgentSdkReferee(engine, paths, client_factory=factory), clients


def run_turn(referee, text="I look around."):
    async def collect():
        return [e for e in [event async for event in referee.turn(text)] if e is not None]

    return asyncio.run(collect())


def test_options_load_no_user_settings_and_turn_off_memory_and_auto_compact(engine, paths):
    referee, clients = make_referee(engine, paths, [result()])
    run_turn(referee)
    options = clients[0].options

    assert options.setting_sources == []
    assert options.env["CLAUDE_CODE_DISABLE_AUTO_MEMORY"] == "1"
    assert options.env["DISABLE_AUTO_COMPACT"] == "1"
    assert options.tools == ["Read", "Write", "Edit", "Glob", "Grep"]
    assert sorted(options.allowed_tools) == ["mcp__engine__move", "mcp__engine__propose", "mcp__engine__state"]
    assert options.cwd == str(paths.vault)
    assert options.add_dirs == [str(paths.referee)]
    assert (options.model, options.effort) == ("sonnet", "low")
    assert "OSE" in options.system_prompt
    assert str(paths.referee) in options.system_prompt


def test_the_system_prompt_holds_the_vault_conventions_note_as_the_owner_left_it(engine, paths):
    conventions = paths.vault / "Conventions.md"
    conventions.write_text(conventions.read_text() + "\n- Name every tavern after a bird.\n")
    referee, clients = make_referee(engine, paths, [result()])
    run_turn(referee)

    assert "Name every tavern after a bird." in clients[0].options.system_prompt


def test_the_pre_tool_use_hook_is_the_path_guard(engine, paths):
    referee, clients = make_referee(engine, paths, [result()])
    run_turn(referee)
    hook = clients[0].options.hooks["PreToolUse"][0].hooks[0]

    async def decide(tool_input):
        return await hook({"tool_name": "Write", "tool_input": tool_input}, "t1", {})

    denied = asyncio.run(decide({"file_path": "State.md", "content": "x"}))
    allowed = asyncio.run(decide({"file_path": "NPCs/Mag.md", "content": "x"}))

    assert denied["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert allowed == {}


def test_can_use_tool_denies_every_permission_prompt(engine, paths):
    referee, clients = make_referee(engine, paths, [result()])
    run_turn(referee)

    decision = asyncio.run(clients[0].options.can_use_tool("Read", {"file_path": "/etc/hostname"}, None))

    assert isinstance(decision, sdk.PermissionResultDeny)


def test_loaded_memory_files_stop_the_referee(engine, paths):
    referee, _ = make_referee(engine, paths, [result()], memory_files=[{"path": "MEMORY.md", "type": "AutoMem"}])

    with pytest.raises(RefereeConfigError, match="MEMORY.md"):
        run_turn(referee)


def test_streamed_text_and_a_tool_call_become_referee_events(engine, paths):
    referee, clients = make_referee(
        engine,
        paths,
        [
            delta("Checking the door."),
            tool_use("t1", "mcp__engine__move", {"to": "hall"}),
            run_engine_tool("move", {"to": "hall"}),
            tool_result("t1"),
            delta("You enter the hall."),
            assistant(sdk.TextBlock(text="You enter the hall.")),
            result(),
        ],
    )

    events = run_turn(referee)

    assert [e["type"] for e in events] == ["text", "tool_start", "tool_result", "text", "done"]
    assert events[1]["label"] == "Moving to Long Hall"
    assert [e["type"] for e in events[2]["events"]] == ["moved", "area_revealed"]
    assert engine.state()["party"]["area"] == "hall"
    assert clients[0].queries[0].endswith("I look around.")
    assert '"area": "gate"' in clients[0].queries[0]


def test_a_tool_call_the_guard_denied_is_a_denied_result(engine, paths):
    referee, _ = make_referee(
        engine,
        paths,
        [
            tool_use("t1", "Read", {"file_path": "/etc/hostname"}),
            run_hook("Read", {"file_path": "/etc/hostname"}, "t1"),
            tool_result("t1", is_error=True, content="denied"),
            result(),
        ],
    )

    events = run_turn(referee)

    assert events[1]["denied"] is True and events[1]["ok"] is False


def test_a_failed_engine_tool_is_a_failed_result_with_the_engine_message(engine, paths):
    referee, _ = make_referee(
        engine,
        paths,
        [
            tool_use("t1", "mcp__engine__move", {"to": "crypt"}),
            run_engine_tool("move", {"to": "crypt"}),
            tool_result("t1", is_error=True),
            result(),
        ],
    )

    events = run_turn(referee)

    assert events[1]["ok"] is False
    assert "crypt" in events[1]["error"]


def test_the_client_connects_once_per_session_and_closes(engine, paths):
    referee, clients = make_referee(engine, paths, [result()], [result()])

    run_turn(referee)
    run_turn(referee)
    asyncio.run(referee.close())

    assert len(clients) == 1
    assert clients[0].disconnected
