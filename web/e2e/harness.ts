import { spawn, spawnSync, type ChildProcess } from 'node:child_process'
import { existsSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { createServer } from 'node:net'
import { tmpdir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))
const repo = resolve(here, '..', '..')

export interface Harness {
  url: string
  campaign: string
  stop: () => Promise<void>
}

export interface HarnessOptions {
  seed?: number
  /** Edits the demo campaign's engine state before the server opens it. */
  editState?: (state: Record<string, any>) => void
}

/** The `solo-harness` of this checkout's venv, else the one on the PATH. */
function harnessBin(): string {
  const venv = join(repo, '.venv', 'bin', 'solo-harness')
  return process.env.SOLO_HARNESS_BIN ?? (existsSync(venv) ? venv : 'solo-harness')
}

function freePort(): Promise<number> {
  return new Promise((done, fail) => {
    const probe = createServer()
    probe.once('error', fail)
    probe.listen(0, '127.0.0.1', () => {
      const { port } = probe.address() as { port: number }
      probe.close(() => done(port))
    })
  })
}

async function waitFor(url: string, child: ChildProcess, log: () => string): Promise<void> {
  const deadline = Date.now() + 30_000
  while (Date.now() < deadline) {
    if (child.exitCode !== null) throw new Error(`solo-harness exited early:\n${log()}`)
    try {
      if ((await fetch(url)).ok) return
    } catch {
      // not listening yet
    }
    await new Promise((r) => setTimeout(r, 100))
  }
  throw new Error(`solo-harness did not answer at ${url}:\n${log()}`)
}

/**
 * Makes a demo campaign in a temp folder and serves it on a free port with no Referee
 * and a fixed dice seed. Needs `web/dist` built (`npm run build`).
 */
export async function startHarness(options: HarnessOptions = {}): Promise<Harness> {
  const bin = harnessBin()
  const dir = mkdtempSync(join(tmpdir(), 'harness-e2e-'))
  const campaign = join(dir, 'demo')
  const demo = spawnSync(bin, ['demo', campaign], { encoding: 'utf8' })
  if (demo.status !== 0) throw new Error(`solo-harness demo failed:\n${demo.stderr}`)

  if (options.editState) {
    const file = join(campaign, 'engine', 'state.json')
    const state = JSON.parse(readFileSync(file, 'utf8'))
    options.editState(state)
    writeFileSync(file, JSON.stringify(state, null, 2))
  }

  const port = await freePort()
  const child = spawn(
    bin,
    ['serve', campaign, '--referee', 'none', '--seed', String(options.seed ?? 7), '--port', String(port),
     '--web-dist', join(repo, 'web', 'dist')],
    { stdio: ['ignore', 'pipe', 'pipe'] },
  )
  let output = ''
  child.stdout?.on('data', (chunk) => (output += chunk))
  child.stderr?.on('data', (chunk) => (output += chunk))

  const url = `http://127.0.0.1:${port}/`
  try {
    await waitFor(url, child, () => output)
  } catch (error) {
    child.kill()
    rmSync(dir, { recursive: true, force: true })
    throw error
  }
  return {
    url,
    campaign,
    stop: async () => {
      if (child.exitCode === null) {
        const exited = new Promise((r) => child.once('exit', r))
        child.kill('SIGTERM')
        await exited
      }
      rmSync(dir, { recursive: true, force: true })
    },
  }
}
