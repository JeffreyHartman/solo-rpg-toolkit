<!-- The campaign settings menu: the confirm level of each procedure. -->
<script lang="ts">
  import type { ConfirmLevel } from './protocol'
  import { game, setConfirmLevel, setOption } from './socket.svelte'

  let { onclose }: { onclose: () => void } = $props()
</script>

<section class="settings">
  <header>
    <b>Campaign settings</b>
    <button onclick={onclose} aria-label="Close the campaign settings">Close</button>
  </header>
  {#each game.settings?.options ?? [] as row (row.section + row.key)}
    <label>
      <span>{row.label}</span>
      <select value={row.value} onchange={(e) => setOption(row.section, row.key, e.currentTarget.value)}>
        {#each row.choices as choice (choice)}
          <option value={choice}>{choice}</option>
        {/each}
      </select>
    </label>
  {/each}
  <h3 class="smallcaps dim">Confirm levels</h3>
  <div class="rows scroll">
    {#each game.settings?.confirm ?? [] as row (row.procedure)}
      <label>
        <span>{row.label}</span>
        <select
          value={row.level}
          onchange={(e) => setConfirmLevel(row.procedure, e.currentTarget.value as ConfirmLevel)}
        >
          <option value="auto">Auto</option>
          <option value="confirm">Confirm</option>
        </select>
      </label>
    {/each}
  </div>
</section>

<style>
  .settings { display: flex; flex-direction: column; gap: 6px; max-height: 60vh; }
  header { display: flex; justify-content: space-between; align-items: center; gap: 12px; }
  h3 { margin: 4px 0 0; font-size: 13px; font-weight: normal; }
  .rows { display: flex; flex-direction: column; gap: 4px; }
  label { display: flex; justify-content: space-between; align-items: center; gap: 12px; }
</style>
