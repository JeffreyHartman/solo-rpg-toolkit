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

export interface LightSource {
  kind: string
  bearer: string | null
  turns_left: number
}

export interface Dungeon {
  turn: number
  light: LightSource[]
  turns_since_rest: number
}

export interface Target {
  value: number
  source: string
  editable?: boolean
}

export interface InputSpec {
  type: 'string' | 'integer'
  label: string
  choices?: string[]
  default?: string | number
}

export interface Proposal {
  id: string
  procedure: string
  label: string
  inputs: Record<string, string | number>
  target: Target | null
  reason: string
}

export interface EngineState {
  session: number
  party: { members: Member[]; area: string }
  map: { areas: Record<string, Area>; connections: Connection[]; open_exits?: OpenExit[] }
  dungeon?: Dungeon
  proposals?: { pending: Proposal[] }
}

export type ConfirmLevel = 'auto' | 'confirm'

export interface ConfirmRow {
  procedure: string
  label: string
  default: ConfirmLevel
  level: ConfirmLevel
}

export interface CampaignSettings {
  confirm: ConfirmRow[]
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
  | { type: 'snapshot'; state: EngineState; actions: Action[]; settings: CampaignSettings }
  | { type: 'events'; events: EngineEvent[]; state: EngineState; actions: Action[] }
  | { type: 'player'; text: string }
  | { type: 'referee'; event: RefereeEvent }
  | { type: 'settings'; settings: CampaignSettings }
  | { type: 'error'; message: string }

export type ProposalAnswer = 'confirm' | 'change' | 'reject'

export type ClientMessage =
  | { type: 'act'; command: Command }
  | { type: 'say'; text: string }
  | { type: 'answer'; id: string; answer: ProposalAnswer; inputs?: Record<string, string | number> }
  | { type: 'set_setting'; section: string; key: string; value: unknown }
