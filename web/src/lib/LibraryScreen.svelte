<!-- New campaign and Open campaign: pick a saved campaign, or choose plugins for a new one. -->
<script lang="ts">
  import { game, newCampaign, openCampaign } from './socket.svelte'

  let name = $state('')
  let ruleset = $state('')
  let generators = $state<string[]>([])
  let module = $state('')

  let plugins = $derived(game.library?.plugins)
  let lastError = $derived.by(() => {
    const last = game.chat.at(-1)
    return last?.kind === 'error' ? last.text : ''
  })
  $effect(() => {
    if (!ruleset && plugins?.ruleset.length) ruleset = plugins.ruleset[0]
  })

  function submit(event: SubmitEvent): void {
    event.preventDefault()
    newCampaign(name, ruleset, generators, module || undefined)
  }
</script>

{#if game.library && plugins}
  <main class="library">
    <section>
      <h2>Open campaign</h2>
      {#each game.library.campaigns as c (c.id)}
        <button class="row" onclick={() => openCampaign(c.id)}>
          <b>{c.name}</b>
          <span class="dim">{c.members.join(', ') || 'no character yet'} · session {c.session} · {c.plugins.join(', ')}</span>
        </button>
      {:else}
        <p class="dim">No saved campaigns.</p>
      {/each}
    </section>
    <form onsubmit={submit}>
      <h2>New campaign</h2>
      <label>Name <input bind:value={name} required /></label>
      <label>Ruleset
        <select bind:value={ruleset}>
          {#each plugins.ruleset as p (p)}<option>{p}</option>{/each}
        </select>
      </label>
      <fieldset>
        <legend>Generators</legend>
        {#each plugins.generator as p (p)}
          <label class="check"><input type="checkbox" value={p} bind:group={generators} /> {p}</label>
        {:else}<span class="dim">None installed.</span>{/each}
      </fieldset>
      <label>Module
        <select bind:value={module}>
          <option value="">None</option>
          {#each plugins.module as p (p)}<option>{p}</option>{/each}
        </select>
      </label>
      <button class="primary" disabled={!name.trim() || !ruleset}>Create</button>
    </form>
    {#if lastError}<p class="err">{lastError}</p>{/if}
  </main>
{/if}

<style>
  .library { position: fixed; inset: 0; overflow: auto; display: flex; flex-wrap: wrap; gap: 24px; padding: 24px; background: var(--bg); }
  section, form { flex: 1 1 320px; display: flex; flex-direction: column; gap: 8px; max-width: 480px; }
  .row { display: flex; flex-direction: column; text-align: left; }
  label, fieldset { display: flex; flex-direction: column; gap: 2px; border: 0; padding: 0; }
  label.check { flex-direction: row; align-items: center; gap: 8px; }
  label.check input { width: auto; margin: 0; }
  .err { color: var(--bad); }
</style>
