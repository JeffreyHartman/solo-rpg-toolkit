"""`AgentSdkReferee`: the Referee on the Claude Agent SDK, signed in with the player's plan.

The options follow ADR 0002. The SDK version is pinned in the `harness` extra;
on every upgrade, check that `memoryFiles` in the context usage is still empty.
"""
import json
from collections import defaultdict, deque
from collections.abc import AsyncIterator, Callable
from typing import Any

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    HookMatcher,
    PermissionResultDeny,
    ResultMessage,
    StreamEvent,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
    create_sdk_mcp_server,
    tool,
)

from ..campaign import CampaignPaths
from ..engine import Engine
from ..errors import HarnessError
from . import events
from .base import turn_prompt
from .guard import ENGINE_TOOL_PREFIX, FILE_TOOLS
from .tools import EngineTool, RefereeTools, ToolOutcome

__all__ = ["AgentSdkReferee", "RefereeConfigError", "system_prompt"]

DEFAULT_MODEL = "sonnet"
DEFAULT_EFFORT = "low"

ClientFactory = Callable[[ClaudeAgentOptions], Any]


class RefereeConfigError(HarnessError):
    """The Agent SDK session loaded something the Referee must not have."""


BASE_PROMPT = """You are the Referee of a solo tabletop RPG campaign. One player plays the party.

- Narrate in second person, in two to four short paragraphs, then stop and let the player act.
- The engine owns all mechanical state and every die roll. Never invent a die result, a damage number, an HP change, or a position change. Change mechanical state only with the `mcp__engine__*` tools.
- Each player message starts with a fresh <state> snapshot from the engine. Trust it over anything you remember.
- Before a tool call, write at most one short status line, or nothing. Write the narration after the last tool call.
- Your working directory is the campaign vault, an Obsidian folder of markdown records with YAML frontmatter and [[wikilinks]]. Read records to learn the story, and write records for new NPCs, places, threads, and clues.
- The engine writes `State.md` and everything in `Sessions/Raw/`. Read them, but never write or edit them.
- Keep secrets the player must not see yet (unfound traps, hidden plans) in the referee folder: {referee}
- You can reach only the vault and the referee folder. You have no shell and no web.
"""


def system_prompt(guides: list[str], paths: CampaignPaths) -> str:
    """The Referee's system prompt: the base rules, then each plugin's Referee guide."""
    return "\n\n".join([BASE_PROMPT.format(referee=paths.referee), *guides])


class AgentSdkReferee:
    def __init__(
        self,
        engine: Engine,
        paths: CampaignPaths,
        model: str = DEFAULT_MODEL,
        effort: str = DEFAULT_EFFORT,
        client_factory: ClientFactory = ClaudeSDKClient,
    ):
        paths.vault.mkdir(parents=True, exist_ok=True)
        paths.referee.mkdir(parents=True, exist_ok=True)
        self._tools = RefereeTools(engine, paths)
        self._model = model
        self._effort = effort
        self._client_factory = client_factory
        self._client: Any = None
        self._denied: dict[str, str] = {}
        self._outcomes: dict[str, deque[ToolOutcome | HarnessError]] = defaultdict(deque)
        self._started: dict[str, str] = {}

    def options(self) -> ClaudeAgentOptions:
        server = create_sdk_mcp_server("engine", tools=[self._mcp_tool(t) for t in self._tools.engine_tools.values()])
        paths = self._tools.paths
        return ClaudeAgentOptions(
            system_prompt=system_prompt(self._tools.engine.referee_guides(), paths),
            setting_sources=[],
            env={"CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1", "DISABLE_AUTO_COMPACT": "1"},
            tools=list(FILE_TOOLS),
            allowed_tools=self._tools.engine_tool_names,
            mcp_servers={"engine": server},
            strict_mcp_config=True,
            cwd=str(paths.vault),
            add_dirs=[str(paths.referee)],
            permission_mode="acceptEdits",
            hooks={"PreToolUse": [HookMatcher(matcher=None, hooks=[self._pre_tool_use])]},
            can_use_tool=_deny_all,
            model=self._model,
            effort=self._effort,
            include_partial_messages=True,
        )

    async def turn(self, player_input: str) -> AsyncIterator[events.RefereeEvent]:
        client = await self._connect()
        await client.query(turn_prompt(player_input, self._tools.engine.state()))
        async for message in client.receive_response():
            for event in self._translate(message):
                yield event

    async def close(self) -> None:
        if self._client is not None:
            await self._client.disconnect()
            self._client = None

    async def _connect(self) -> Any:
        if self._client is None:
            client = self._client_factory(self.options())
            await client.connect()
            usage = await client.get_context_usage()
            loaded = usage.get("memoryFiles") or []
            if loaded:
                await client.disconnect()
                names = ", ".join(str(m.get("path", m)) if isinstance(m, dict) else str(m) for m in loaded)
                raise RefereeConfigError(f"the Referee session loaded memory files: {names}")
            self._client = client
        return self._client

    def _translate(self, message: Any) -> list[events.RefereeEvent]:
        if isinstance(message, StreamEvent):
            if message.parent_tool_use_id is None:
                delta = message.event.get("delta", {})
                if message.event.get("type") == "content_block_delta" and delta.get("type") == "text_delta":
                    return [events.text(delta["text"])]
        elif isinstance(message, AssistantMessage) and message.parent_tool_use_id is None:
            started = []
            for block in message.content:
                if isinstance(block, ToolUseBlock):
                    self._started[block.id] = block.name
                    label = self._tools.label(block.name, block.input)
                    started.append(events.tool_start(block.id, block.name, block.input, label))
            return started
        elif isinstance(message, UserMessage) and isinstance(message.content, list):
            return [self._tool_result(b) for b in message.content if isinstance(b, ToolResultBlock)]
        elif isinstance(message, ResultMessage):
            error = (message.result or "the Referee turn failed") if message.is_error else None
            return [events.done(error=error)]
        return []

    def _tool_result(self, block: ToolResultBlock) -> events.RefereeEvent:
        tool_name = self._started.pop(block.tool_use_id, "")
        reason = self._denied.pop(block.tool_use_id, None)
        if reason is not None:
            return events.tool_result(block.tool_use_id, tool_name, ok=False, denied=True, error=reason)
        if tool_name.startswith(ENGINE_TOOL_PREFIX) and self._outcomes[tool_name]:
            outcome = self._outcomes[tool_name].popleft()
            if isinstance(outcome, HarnessError):
                return events.tool_result(block.tool_use_id, tool_name, ok=False, error=str(outcome))
            return events.tool_result(
                block.tool_use_id, tool_name, ok=True, output=outcome.output, events=outcome.events
            )
        error = _content_text(block.content) if block.is_error else None
        return events.tool_result(block.tool_use_id, tool_name, ok=not block.is_error, error=error)

    def _mcp_tool(self, engine_tool: EngineTool):
        full_name = ENGINE_TOOL_PREFIX + engine_tool.name

        async def handler(args: dict[str, Any]) -> dict[str, Any]:
            try:
                outcome = self._tools.run_engine(full_name, args)
            except HarnessError as exc:
                # The tool result block does not carry this text back, so keep it for `_tool_result`.
                self._outcomes[full_name].append(exc)
                return {"content": [{"type": "text", "text": str(exc)}], "is_error": True}
            self._outcomes[full_name].append(outcome)
            return {"content": [{"type": "text", "text": json.dumps(outcome.output)}]}

        return tool(engine_tool.name, engine_tool.description, engine_tool.input_schema)(handler)

    async def _pre_tool_use(self, input_data: dict[str, Any], tool_use_id: str | None, context: Any) -> dict[str, Any]:
        reason = self._tools.guard.check(input_data["tool_name"], input_data.get("tool_input") or {})
        if reason is None:
            return {}
        if tool_use_id:
            self._denied[tool_use_id] = reason
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        }


async def _deny_all(tool_name: str, tool_input: dict[str, Any], context: Any) -> PermissionResultDeny:
    return PermissionResultDeny(message=f"The harness allows no permission prompts ({tool_name}).")


def _content_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(str(part.get("text", "")) for part in content if isinstance(part, dict))
    return ""
