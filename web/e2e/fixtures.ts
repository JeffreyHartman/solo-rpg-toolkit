import { test as base } from '@playwright/test'
import { startHarness, type Harness, type HarnessOptions } from './harness.ts'

/** Sends one browser-to-server message from Node; the server broadcasts its results to the page too. */
export async function sendMessage(harness: Harness, message: Record<string, unknown>): Promise<void> {
  const socket = new WebSocket(harness.url.replace(/^http/, 'ws') + 'ws')
  await new Promise<void>((done, fail) => {
    socket.onerror = () => fail(new Error('websocket failed'))
    socket.onmessage = () => {
      // The first message is the snapshot; the command goes after it.
      socket.send(JSON.stringify(message))
      setTimeout(() => {
        socket.close()
        done()
      }, 300)
      socket.onmessage = null
    }
  })
}

type Fixtures = {
  /** Starts a demo harness; each one stops at the end of the test. */
  launch: (options?: HarnessOptions) => Promise<Harness>
}

export const test = base.extend<Fixtures>({
  launch: async ({}, use) => {
    const started: Harness[] = []
    await use(async (options) => {
      const harness = await startHarness(options)
      started.push(harness)
      return harness
    })
    await Promise.all(started.map((h) => h.stop()))
  },
})

export { expect } from '@playwright/test'
