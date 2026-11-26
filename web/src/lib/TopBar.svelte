<!-- The top bar: Referee model and effort, the context reading against the budget, and the session controls. -->
<script lang="ts">
  import { EFFORTS, MODELS, type RefereeSettings } from './protocol'
  import { control, game, setRefereeSetting } from './socket.svelte'

  let { ondrawer, onsettings }: { ondrawer: () => void; onsettings: () => void } = $props()

  let referee = $derived(game.settings?.referee)
  let reading = $derived(game.context)

  function kilo(tokens: number): string {
    return tokens >= 1000 ? `${(tokens / 1000).toFixed(1)}k` : String(tokens)
  }

  function newSession(): void {
    if (confirm('Start a new session? The Referee starts a new conversation from the state and the vault.')) {
      control('new_session')
    }
  }

  function endSession(): void {
    if (confirm('End the session? The Referee writes the session note and updates the records.')) {
      control('end_session')
    }
  }
</script>

<header class="bar">
  {#if referee}
    <label>
      <span class="smallcaps dim">Model</span>
      <select
        value={referee.model}
        onchange={(e) => setRefereeSetting('model', e.currentTarget.value as RefereeSettings['model'])}
      >
        {#each MODELS as model (model)}<option value={model}>{model}</option>{/each}
      </select>
    </label>
    <label>
      <span class="smallcaps dim">Effort</span>
      <select
        value={referee.effort}
        onchange={(e) => setRefereeSetting('effort', e.currentTarget.value as RefereeSettings['effort'])}
      >
        {#each EFFORTS as effort (effort)}<option value={effort}>{effort}</option>{/each}
      </select>
    </label>
  {/if}
  <button
    class="reading"
    class:over={reading?.over}
    onclick={ondrawer}
    title={reading?.over ? 'The context is over the budget. Compact or start a new session when it suits you.' : 'Show what the Referee got this turn'}
  >
    Context {reading?.tokens != null ? kilo(reading.tokens) : '–'} / {kilo(reading?.budget ?? referee?.budget ?? 0)}
    {#if reading?.over}<span class="tag">over budget</span>{/if}
  </button>
  <button onclick={() => control('compact')} disabled={game.control !== null}>
    {game.control === 'compact' ? 'Compacting…' : 'Compact'}
  </button>
  <button onclick={newSession} disabled={game.control !== null}>New session</button>
  <button onclick={endSession} disabled={game.control !== null}>
    {game.control === 'end_session' ? 'Ending…' : 'End session'}
  </button>
  <button onclick={onsettings}>Settings</button>
</header>

<style>
  .bar { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; }
  label { display: flex; align-items: center; gap: 4px; }
  .reading.over { border-color: var(--warn); color: var(--warn); }
  .tag { margin-left: 4px; font-size: 12px; }
  button:disabled { opacity: 0.5; cursor: default; }
</style>
