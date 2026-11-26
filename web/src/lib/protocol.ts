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
  class?: string
  level?: number
  description?: string
  abilities?: Record<string, number>
  hp?: number
  max_hp?: number
}

export interface CampaignSummary {
  id: string
  name: string
  plugins: string[]
  members: string[]
  session: number
}

export type PluginsByKind = Record<'ruleset' | 'generator' | 'module', string[]>

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

export interface JudgmentCall {
  id: string
  category: string
  question: string
  suggestion: string
  reason: string
  options: string[]
}

export interface Monster {
  id: string
  name: string
  hp: number
  max_hp: number
  ac: number
  status: 'alive' | 'dead' | 'fled'
}

export interface Combat {
  round: number
  phase: 'party' | 'monsters'
  monsters: Monster[]
}

export interface EngineState {
  session: number
  party: { members: Member[]; area: string }
  map: { areas: Record<string, Area>; connections: Connection[]; open_exits?: OpenExit[] }
  dungeon?: Dungeon
  combat?: Combat | null
  proposals?: { pending: Proposal[] }
  judgments?: { pending: JudgmentCall[] }
}

export type ConfirmLevel = 'auto' | 'confirm'

export interface ConfirmRow {
  procedure: string
  label: string
  default: ConfirmLevel
  level: ConfirmLevel
}

export const MODELS = ['sonnet', 'opus', 'haiku'] as const
export const EFFORTS = ['low', 'medium', 'high', 'xhigh', 'max'] as const

export interface RefereeSettings {
  model: (typeof MODELS)[number]
  effort: (typeof EFFORTS)[number]
  budget: number
}

export interface OptionRow {
  section: string
  key: string
  label: string
  choices: string[]
  default: string
  value: string
}

export type JudgmentOwner = 'ask' | 'referee'

export interface JudgmentRow {
  category: string
  label: string
  owner: JudgmentOwner
}

export interface CampaignSettings {
  confirm: ConfirmRow[]
  options?: OptionRow[]
  judgment: JudgmentRow[]
  referee: RefereeSettings
}

// One thing the Referee got in its latest turn, from Referee.turn_context.
export interface ContextPart {
  label: string
  chars: number
  text: string
}

export interface ContextReading {
  type: 'context'
  tokens: number | null
  budget: number
  over: boolean
  parts: ContextPart[]
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
  | {
      type: 'snapshot'
      state: EngineState
      actions: Action[]
      settings: CampaignSettings
      context: ContextReading | null
    }
  | { type: 'events'; events: EngineEvent[]; state: EngineState; actions: Action[] }
  | { type: 'library'; campaigns: CampaignSummary[]; plugins: PluginsByKind }
  | { type: 'player'; text: string }
  | { type: 'referee'; event: RefereeEvent }
  | { type: 'settings'; settings: CampaignSettings }
  | ContextReading
  | { type: 'session'; session: number; note: string | null }
  | { type: 'error'; message: string }

export type ProposalAnswer = 'confirm' | 'change' | 'reject'

export type ClientMessage =
  | { type: 'act'; command: Command }
  | { type: 'say'; text: string }
  | { type: 'answer'; id: string; answer: ProposalAnswer; inputs?: Record<string, string | number> }
  | { type: 'answer_judgment'; id: string; answer: string }
  | { type: 'set_setting'; section: string; key: string; value: unknown }
  | { type: 'compact' }
  | { type: 'new_session' }
  | { type: 'end_session' }
  | { type: 'list_campaigns' }
  | { type: 'new_campaign'; name: string; ruleset: string; generators: string[]; module?: string }
  | { type: 'open_campaign'; id: string }
