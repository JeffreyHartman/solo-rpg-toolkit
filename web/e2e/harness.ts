import { spawn, spawnSync, type ChildProcess } from 'node:child_process'
import { cpSync, existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
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

  const { url, child } = await serve(bin, dir, ['serve', campaign, '--referee', 'none', '--seed', String(options.seed ?? 7)])
  return { url, campaign, stop: () => stopServer(child, dir) }
}

async function stopServer(child: ChildProcess, dir: string): Promise<void> {
  if (child.exitCode === null) {
    const exited = new Promise((r) => child.once('exit', r))
    child.kill('SIGTERM')
    await exited
  }
  rmSync(dir, { recursive: true, force: true })
}

/** Starts `solo-harness` with `args` plus a free port and the built web app; removes `dir` if it fails. */
async function serve(bin: string, dir: string, args: string[], env: Record<string, string> = {}) {
  const port = await freePort()
  const child = spawn(bin, [...args, '--port', String(port), '--web-dist', join(repo, 'web', 'dist')], {
    stdio: ['ignore', 'pipe', 'pipe'],
    env: { ...process.env, ...env },
  })
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
  return { url, child, output }
}

export interface ScriptedHarness {
  url: string
  /** The folder that holds the campaigns the browser creates. */
  campaigns: string
  stop: () => Promise<void>
}

/**
 * Serves an empty campaign folder with the `ScriptedReferee` and fixed dice from `script`
 * (`solo-harness serve --script`). The synthetic FlexTale tables in `e2e/data/flextale` are the
 * generator's data, so no book text is involved.
 */
export async function startScriptedHarness(script: Record<string, unknown>): Promise<ScriptedHarness> {
  const dir = mkdtempSync(join(tmpdir(), 'harness-e2e-'))
  const campaigns = join(dir, 'campaigns')
  const data = join(dir, 'xdg')
  mkdirSync(campaigns)
  cpSync(join(here, 'data', 'flextale'), join(data, 'solo-rpg-toolkit', 'flextale'), { recursive: true })
  const scriptFile = join(dir, 'script.json')
  writeFileSync(scriptFile, JSON.stringify(script))
  const { url, child } = await serve(
    harnessBin(), dir, ['serve', '--campaigns', campaigns, '--referee', 'scripted', '--script', scriptFile],
    { XDG_DATA_HOME: data },
  )
  return { url, campaigns, stop: () => stopServer(child, dir) }
}
