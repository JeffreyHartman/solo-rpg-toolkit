<!-- The campaign settings menu: the Referee model, effort and context budget, the confirm level of each procedure, and the owner of each judgment call category. -->
<script lang="ts">
  import { EFFORTS, MODELS, type ConfirmLevel, type JudgmentOwner, type RefereeSettings } from './protocol'
  import { game, setConfirmLevel, setJudgmentOwner, setRefereeSetting } from './socket.svelte'

  function setBudget(raw: string): void {
    const budget = Number(raw)
    if (Number.isInteger(budget) && budget > 0) setRefereeSetting('budget', budget)
  }

  let { onclose }: { onclose: () => void } = $props()
</script>

<section class="settings">
  <header>
    <b>Campaign settings</b>
    <button onclick={onclose} aria-label="Close the campaign settings">Close</button>
  </header>
  {#if game.settings?.referee}
    <h3 class="smallcaps dim">Referee</h3>
    <div class="rows">
      <label>
        <span>Model</span>
        <select
          value={game.settings.referee.model}
          onchange={(e) => setRefereeSetting('model', e.currentTarget.value as RefereeSettings['model'])}
        >
          {#each MODELS as model (model)}<option value={model}>{model}</option>{/each}
        </select>
      </label>
      <label>
        <span>Effort</span>
        <select
          value={game.settings.referee.effort}
          onchange={(e) => setRefereeSetting('effort', e.currentTarget.value as RefereeSettings['effort'])}
        >
          {#each EFFORTS as effort (effort)}<option value={effort}>{effort}</option>{/each}
        </select>
      </label>
      <label>
        <span>Context budget (tokens)</span>
        <input
          type="number"
          min="1000"
          step="1000"
          value={game.settings.referee.budget}
          onchange={(e) => setBudget(e.currentTarget.value)}
        />
      </label>
    </div>
  {/if}
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
  <h3 class="smallcaps dim">Judgment calls</h3>
  <div class="rows scroll">
    {#each game.settings?.judgment ?? [] as row (row.category)}
      <label>
        <span>{row.label}</span>
        <select
          value={row.owner}
          onchange={(e) => setJudgmentOwner(row.category, e.currentTarget.value as JudgmentOwner)}
        >
          <option value="ask">Ask me</option>
          <option value="referee">Referee decides</option>
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
  input { width: 9em; }
  label { display: flex; justify-content: space-between; align-items: center; gap: 12px; }
</style>
