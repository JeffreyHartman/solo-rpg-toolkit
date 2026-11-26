// Mirrors the messages in src/solo_roll/harness/server.py.

export interface Area {
  name: string
  x: number
  y: number
  w: number
  h: number
  known: boolean
}

export interface Connection {
  id: string
  a: string
  b: string
  label?: string
}

export interface Member {
  name: string
}

export interface EngineState {
  session: number
  party: { members: Member[]; area: string }
  map: { areas: Record<string, Area>; connections: Connection[] }
}

export interface Command {
  type: string
  [field: string]: unknown
}

export interface Action {
  id: string
  label: string
  command: Command
}

export interface EngineEvent {
  type: string
  text?: string
  [field: string]: unknown
}

// Mirrors src/solo_roll/harness/referee/events.py. Text before a tool_start in a
// turn is a status line, not narration.
export type RefereeEvent =
  | { type: 'text'; text: string }
  | { type: 'tool_start'; id: string; tool: string; input: Record<string, unknown>; label: string }
  | {
      type: 'tool_result'
      id: string
      tool: string
      ok: boolean
      denied: boolean
      output?: unknown
      error?: string
      events: EngineEvent[]
    }
  | { type: 'done'; error?: string }

export type ServerMessage =
  | { type: 'snapshot'; state: EngineState; actions: Action[] }
  | { type: 'events'; events: EngineEvent[]; state: EngineState; actions: Action[] }
  | { type: 'player'; text: string }
  | { type: 'referee'; event: RefereeEvent }
  | { type: 'error'; message: string }

export type ClientMessage = { type: 'act'; command: Command } | { type: 'say'; text: string }
