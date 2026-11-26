import type {
  Action,
  CampaignSettings,
  CampaignSummary,
  ClientMessage,
  Command,
  ConfirmLevel,
  EngineState,
  PluginsByKind,
  JudgmentOwner,
  ProposalAnswer,
  RefereeEvent,
  ServerMessage,
  Target,
} from './protocol'

export interface MechanicsCard {
  dice: string
  rolls: number[]
  total: number
  result: string
  source: string
  target?: Target
}

export type ChatEntry =
  | { kind: 'player' | 'narration' | 'status' | 'event' | 'error'; text: string }
  | { kind: 'mechanics'; text: string; card: MechanicsCard }
  | { kind: 'tool'; id: string; label: string; outcome: 'running' | 'ok' | 'failed' | 'denied'; error?: string }

export const game = $state({
  connected: false,
  state: null as EngineState | null,
  actions: [] as Action[],
  chat: [] as ChatEntry[],
  refereeBusy: false,
  settings: null as CampaignSettings | null,
  // Set while the New and Open campaign screen is showing; null while a campaign is open.
  library: null as { campaigns: CampaignSummary[]; plugins: PluginsByKind } | null,
})

// Index in game.chat of the narration this turn is streaming into, or -1.
let openText = -1
let socket: WebSocket | null = null

export function connect(): void {
  const scheme = location.protocol === 'https:' ? 'wss' : 'ws'
  socket = new WebSocket(`${scheme}://${location.host}/ws`)
  socket.onopen = () => (game.connected = true)
  socket.onclose = () => {
    game.connected = false
    setTimeout(connect, 1000)
  }
  socket.onmessage = (message) => receive(JSON.parse(message.data) as ServerMessage)
}

function receive(message: ServerMessage): void {
  switch (message.type) {
    case 'library':
      game.library = { campaigns: message.campaigns, plugins: message.plugins }
      return
    case 'snapshot':
      if (game.library) game.chat = []
      game.library = null
      game.settings = message.settings
      break
    case 'error':
      game.chat.push({ kind: 'error', text: message.message })
      return
    case 'player':
      game.chat.push({ kind: 'player', text: message.text })
      game.refereeBusy = true
      return
    case 'referee':
      onReferee(message.event)
      return
    case 'settings':
      game.settings = message.settings
      return
    case 'events':
      for (const event of message.events) {
        if (event.type === 'mechanics') {
          const { dice, rolls, total, result, source, target } = event as unknown as MechanicsCard
          game.chat.push({
            kind: 'mechanics',
            text: event.text ?? event.type,
            card: { dice, rolls, total, result, source, target },
          })
        } else {
          game.chat.push({ kind: 'event', text: event.text ?? event.type })
        }
      }
      openText = -1
      break
  }
  game.state = message.state
  game.actions = message.actions
}

function onReferee(event: RefereeEvent): void {
  game.refereeBusy = event.type !== 'done'
  if (event.type === 'text') {
    if (openText < 0) {
      game.chat.push({ kind: 'narration', text: '' })
      openText = game.chat.length - 1
    }
    const entry = game.chat[openText]
    if (entry.kind === 'narration') entry.text += event.text
  } else if (event.type === 'tool_start') {
    const open = openText >= 0 ? game.chat[openText] : null
    if (open && open.kind === 'narration') {
      open.kind = 'status'
      open.text = open.text.trim()
    }
    openText = -1
    game.chat.push({ kind: 'tool', id: event.id, label: event.label, outcome: 'running' })
  } else if (event.type === 'tool_result') {
    const entry = game.chat.findLast((e) => e.kind === 'tool' && e.id === event.id)
    if (entry && entry.kind === 'tool') {
      entry.outcome = event.denied ? 'denied' : event.ok ? 'ok' : 'failed'
      entry.error = event.error
    }
  } else {
    openText = -1
    if (event.error) game.chat.push({ kind: 'error', text: `Referee: ${event.error}` })
  }
}

function send(message: ClientMessage): void {
  socket?.send(JSON.stringify(message))
}

export function act(command: Command): void {
  send({ type: 'act', command })
}

export function listCampaigns(): void {
  send({ type: 'list_campaigns' })
}

export function newCampaign(name: string, ruleset: string, generators: string[], module?: string): void {
  send({ type: 'new_campaign', name, ruleset, generators, module })
}

export function openCampaign(id: string): void {
  send({ type: 'open_campaign', id })
}

export const OSE_CLASSES = ['Fighter', 'Cleric', 'Magic-User', 'Thief', 'Dwarf', 'Elf', 'Halfling']

export function createCharacter(characterClass: string, name: string, description: string): void {
  act({ type: 'procedure', name: 'create_character', inputs: { class: characterClass, character_name: name, description } })
}

export function say(text: string): void {
  if (text.trim()) send({ type: 'say', text: text.trim() })
}

export function answer(id: string, reply: ProposalAnswer, inputs?: Record<string, string | number>): void {
  send({ type: 'answer', id, answer: reply, inputs })
}

export function answerJudgment(id: string, reply: string): void {
  send({ type: 'answer_judgment', id, answer: reply })
}

export function setJudgmentOwner(category: string, owner: JudgmentOwner): void {
  send({ type: 'set_setting', section: 'judgment', key: category, value: owner })
}

export function setConfirmLevel(procedure: string, level: ConfirmLevel): void {
  send({ type: 'set_setting', section: 'confirm', key: procedure, value: level })
}

export function setOption(section: string, key: string, value: string): void {
  send({ type: 'set_setting', section, key, value })
}

export function exploreActionFor(exit: string): Action | undefined {
  return game.actions.find((a) => a.command.type === 'explore' && a.command.exit === exit)
}

export function moveActionTo(area: string): Action | undefined {
  return game.actions.find((a) => a.command.type === 'move' && a.command.to === area)
}
