<!-- The context drawer: what the Referee got in its latest turn, part by part, with sizes. -->
<script lang="ts">
  import { game } from './socket.svelte'

  let { onclose }: { onclose: () => void } = $props()

  let parts = $derived(game.context?.parts ?? [])
  let total = $derived(parts.reduce((sum, p) => sum + p.chars, 0))

  // About four characters per token for English prose and JSON; the reading in the top bar is exact.
  function tokens(chars: number): string {
    return `≈${Math.round(chars / 4).toLocaleString()} tokens`
  }
</script>

<section class="drawer">
  <header>
    <b>Context this turn</b>
    <button onclick={onclose} aria-label="Close the context drawer">Close</button>
  </header>
  {#if parts.length}
    <div class="dim">{parts.length} parts, {total.toLocaleString()} characters, {tokens(total)}</div>
    <div class="parts scroll">
      {#each parts as part, i (i)}
        <details>
          <summary>
            <span>{part.label}</span>
            <span class="dim">{part.chars.toLocaleString()} chars · {tokens(part.chars)}</span>
          </summary>
          <pre>{part.text}</pre>
        </details>
      {/each}
    </div>
  {:else}
    <div class="dim">No Referee turn yet in this session.</div>
  {/if}
</section>

<style>
  .drawer { display: flex; flex-direction: column; gap: 6px; height: 100%; }
  header { display: flex; justify-content: space-between; align-items: center; gap: 12px; }
  .parts { display: flex; flex-direction: column; gap: 4px; }
  summary { display: flex; justify-content: space-between; gap: 12px; cursor: pointer; }
  pre { white-space: pre-wrap; word-break: break-word; font-size: 12px; max-height: 40vh; overflow-y: auto; background: var(--panel-2); padding: 6px; border-radius: 6px; }
</style>
