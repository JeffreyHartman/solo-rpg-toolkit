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
        self.models = []
        self.total_tokens = 3700

    async def connect(self):
        self.connected = True

    async def get_context_usage(self):
        return {"totalTokens": self.total_tokens, "memoryFiles": self.memory_files}

    async def set_model(self, model=None):
        self.models.append(model)

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
    assert {
        "mcp__engine__create_character",
        "mcp__engine__judgment_call",
        "mcp__engine__move",
        "mcp__engine__propose",
        "mcp__engine__state",
    } <= set(options.allowed_tools)
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


def run(coro):
    return asyncio.run(coro)


def test_a_new_session_starts_a_new_conversation_that_opens_from_the_vault(engine, paths):
    referee, clients = make_referee(engine, paths, [result()], [result()], [result()])

    run_turn(referee, "one")
    run_turn(referee, "two")
    run(referee.new_session())
    run_turn(referee, "three")

    assert len(clients) == 2
    assert clients[0].disconnected
    assert "<session>" in clients[0].queries[0] and "<session>" not in clients[0].queries[1]
    assert "<session>" in clients[1].queries[0] and clients[1].queries[0].endswith("three")


def test_model_and_effort_changes_apply_to_the_open_conversation(engine, paths):
    referee, clients = make_referee(engine, paths, [result()], [result()], [result()])
    run_turn(referee)

    run(referee.set_model("opus"))
    run(referee.set_effort("high"))
    run_turn(referee)

    assert len(clients) == 1
    assert clients[0].models == ["opus"]
    assert clients[0].queries[1] == "/effort high"
    assert clients[0].queries[2].endswith("I look around.")


def test_model_and_effort_set_before_the_first_turn_go_into_the_options(engine, paths):
    referee, clients = make_referee(engine, paths, [result()])

    run(referee.set_model("opus"))
    run(referee.set_effort("medium"))
    run_turn(referee)

    assert (clients[0].options.model, clients[0].options.effort) == ("opus", "medium")
    assert clients[0].models == []


def test_a_new_conversation_keeps_the_changed_model_and_effort(engine, paths):
    referee, clients = make_referee(engine, paths, [result()], [result()], [result()])
    run_turn(referee)
    run(referee.set_model("opus"))
    run(referee.set_effort("high"))

    run(referee.new_session())
    run_turn(referee)

    assert (clients[1].options.model, clients[1].options.effort) == ("opus", "high")


def test_compact_sends_the_compact_command_and_waits_for_it(engine, paths):
    referee, clients = make_referee(engine, paths, [result()], [result()])
    run_turn(referee)

    run(referee.compact())

    assert clients[0].queries[-1] == "/compact"
    assert clients[0].script == []


def test_compact_before_the_first_turn_does_nothing(engine, paths):
    referee, clients = make_referee(engine, paths)

    run(referee.compact())

    assert clients == []


def test_the_context_reading_is_none_until_the_conversation_starts(engine, paths):
    referee, clients = make_referee(engine, paths, [result()])
    assert run(referee.context_usage()) is None

    run_turn(referee)
    clients[0].total_tokens = 12345

    assert run(referee.context_usage()) == 12345


def test_the_turn_context_lists_what_the_referee_got_with_sizes(engine, paths):
    referee, clients = make_referee(
        engine,
        paths,
        [
            tool_use("t1", "mcp__engine__move", {"to": "hall"}),
            run_engine_tool("move", {"to": "hall"}),
            tool_result("t1", content=[{"type": "text", "text": "moved to hall"}]),
            result(),
        ],
        [result()],
    )

    run_turn(referee, "I walk east.")
    first = referee.turn_context()
    run_turn(referee, "I wait.")
    second = referee.turn_context()

    assert [p["label"] for p in first] == [
        "System prompt", "Session opening", "State snapshot", "Player input", "Moving to Long Hall"
    ]
    assert first[0]["text"] == clients[0].options.system_prompt
    assert first[3] == {"label": "Player input", "chars": len("I walk east."), "text": "I walk east."}
    assert first[4]["text"] == "moved to hall"
    assert all(p["chars"] == len(p["text"]) for p in first)
    assert [p["label"] for p in second] == ["System prompt", "State snapshot", "Player input"]
