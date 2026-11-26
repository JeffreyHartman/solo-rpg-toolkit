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

export interface OpenExit {
  id: string
  area: string
  side: 'n' | 'e' | 's' | 'w'
  label: string
}

export interface Member {
  name: string
}

export interface EngineState {
  session: number
  party: { members: Member[]; area: string }
  map: { areas: Record<string, Area>; connections: Connection[]; open_exits?: OpenExit[] }
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

export type ServerMessage =
  | { type: 'snapshot'; state: EngineState; actions: Action[] }
  | { type: 'events'; events: EngineEvent[]; state: EngineState; actions: Action[] }
  | { type: 'error'; message: string }

export type ClientMessage = { type: 'act'; command: Command }
