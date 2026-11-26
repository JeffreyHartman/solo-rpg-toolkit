<script lang="ts">
  import { game, say } from './socket.svelte'

  let draft = $state('')
  let scroller: HTMLElement | undefined = $state()

  $effect(() => {
    game.chat.length
    game.chat.at(-1)
    scroller?.scrollTo({ top: scroller.scrollHeight })
  })

  function submit(event: SubmitEvent): void {
    event.preventDefault()
    say(draft)
    draft = ''
  }
</script>

<section class="chat">
  <div class="lines scroll" bind:this={scroller}>
    {#each game.chat as entry, i (i)}
      {#if entry.kind === 'tool'}
        <div class="tool {entry.outcome}" title={entry.error ?? ''}>
          {entry.label}{entry.outcome === 'running' ? '…' : ''}
          {#if entry.outcome === 'denied'}<span class="tag">denied</span>{/if}
          {#if entry.outcome === 'failed'}<span class="tag">failed</span>{/if}
        </div>
      {:else if entry.kind === 'mechanics'}
        <div class="card">
          <b>{entry.card.dice}</b> [{entry.card.rolls.join(', ')}] = {entry.card.total}
          {#if entry.card.target}<span> vs {entry.card.target.value}</span>{/if}
          <div>{entry.card.result}</div>
          {#if entry.card.target}<div class="dim">Target: {entry.card.target.source}</div>{/if}
          <div class="dim">{entry.card.source}</div>
        </div>
      {:else if entry.kind === 'ooc'}
        <details class="ooc">
          <summary>Out-of-character note</summary>
          {entry.text}
        </details>
      {:else}
        <div class={entry.kind}>{entry.text}</div>
      {/if}
    {:else}
      <div class="dim">Click an exit or an area to move, or tell the Referee what you do.</div>
    {/each}
    {#if game.refereeBusy}<div class="busy dim">The Referee is working…</div>{/if}
  </div>
  <form onsubmit={submit}>
    <input bind:value={draft} placeholder="What do you do?" aria-label="Free text for the Referee" />
    <button class="primary" type="submit">Send</button>
  </form>
</section>

<style>
  .chat { display: flex; flex-direction: column; gap: 8px; height: 100%; }
  .lines { flex: 1; display: flex; flex-direction: column; gap: 4px; }
  .player { color: var(--accent); font-style: italic; }
  .narration { white-space: pre-wrap; }
  .status, .tool, .event, .busy, .ooc { font-size: 13px; color: var(--ink-dim); }
  .status { font-style: italic; }
  .ooc summary { cursor: pointer; }
  .tool::before { content: '⚙ '; }
  .tool.denied, .tool.failed, .error { color: var(--bad); }
  .card { border: 1px solid #c9a25e66; border-radius: 4px; padding: 4px 6px; font-size: 13px; }
  .tag { margin-left: 6px; font-variant: small-caps; }
  form { display: flex; gap: 6px; }
  input { flex: 1; min-width: 0; }
</style>
