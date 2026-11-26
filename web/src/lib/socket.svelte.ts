import type { Action, ClientMessage, Command, EngineState, ServerMessage } from './protocol'

export interface LogLine {
  kind: 'event' | 'mechanics' | 'error'
  text: string
}

export const game = $state({
  connected: false,
  state: null as EngineState | null,
  actions: [] as Action[],
  log: [] as LogLine[],
})

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
  if (message.type === 'error') {
    game.log.push({ kind: 'error', text: message.message })
    return
  }
  game.state = message.state
  game.actions = message.actions
  if (message.type === 'events') {
    for (const event of message.events) game.log.push({ kind: event.type === 'mechanics' ? 'mechanics' : 'event', text: event.text ?? event.type })
  }
}

function send(message: ClientMessage): void {
  socket?.send(JSON.stringify(message))
}

export function act(command: Command): void {
  send({ type: 'act', command })
}

export function moveActionTo(area: string): Action | undefined {
  return game.actions.find((a) => a.command.type === 'move' && a.command.to === area)
}
