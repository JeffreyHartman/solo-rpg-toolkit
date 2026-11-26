<!-- One pending proposal: the procedure, its inputs, the target number with its source, and the reason. -->
<script lang="ts">
  import type { Proposal } from './protocol'
  import { answer } from './socket.svelte'

  let { proposal }: { proposal: Proposal } = $props()

  let editing = $state(false)
  let draft = $state<Record<string, string | number>>({})

  function startChange(): void {
    draft = { ...proposal.inputs }
    if (proposal.target?.editable) draft.target = proposal.target.value
    editing = true
  }

  function sendChange(event: SubmitEvent): void {
    event.preventDefault()
    answer(proposal.id, 'change', draft)
  }
</script>

<article class="proposal">
  <header><b>{proposal.label}</b> <span class="dim smallcaps">proposal</span></header>
  {#if editing}
    <form onsubmit={sendChange}>
      {#each Object.keys(draft) as name (name)}
        <label>
          <span class="dim">{name}</span>
          <input bind:value={draft[name]} />
        </label>
      {/each}
      <div class="buttons">
        <button class="primary" type="submit">Run with changes</button>
        <button type="button" onclick={() => (editing = false)}>Back</button>
      </div>
    </form>
  {:else}
    <ul class="inputs">
      {#each Object.entries(proposal.inputs) as [name, value] (name)}
        <li><span class="dim">{name}</span> {value}</li>
      {/each}
    </ul>
    {#if proposal.target}
      <div>Target {proposal.target.value} <span class="dim">· {proposal.target.source}</span></div>
    {/if}
    {#if proposal.reason}<div class="reason">{proposal.reason}</div>{/if}
    <div class="buttons">
      <button class="primary" onclick={() => answer(proposal.id, 'confirm')}>Confirm</button>
      <button onclick={startChange}>Change</button>
      <button onclick={() => answer(proposal.id, 'reject')}>Reject</button>
    </div>
  {/if}
</article>

<style>
  .proposal { border: 1px solid var(--accent); border-radius: 8px; padding: 8px 10px; display: flex; flex-direction: column; gap: 4px; font-size: 14px; }
  .inputs { list-style: none; margin: 0; padding: 0; display: flex; flex-wrap: wrap; gap: 4px 12px; }
  .reason { font-style: italic; }
  .buttons { display: flex; gap: 6px; margin-top: 4px; }
  form { display: flex; flex-direction: column; gap: 4px; }
  label { display: flex; gap: 8px; align-items: center; }
  label span { min-width: 72px; }
  input { flex: 1; min-width: 0; }
</style>
