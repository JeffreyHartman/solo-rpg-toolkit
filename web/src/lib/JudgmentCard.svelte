<!-- One pending judgment call: the question, the Referee's suggestion and reason, and the answer buttons. -->
<script lang="ts">
  import type { JudgmentCall } from './protocol'
  import { answerJudgment } from './socket.svelte'

  let { judgment }: { judgment: JudgmentCall } = $props()

  let typed = $state('')

  function sendTyped(event: SubmitEvent): void {
    event.preventDefault()
    if (typed.trim()) answerJudgment(judgment.id, typed.trim())
  }
</script>

<article class="judgment">
  <header><b>{judgment.question}</b> <span class="dim smallcaps">judgment call</span></header>
  <div>The Referee suggests <b>{judgment.suggestion}</b>.</div>
  {#if judgment.reason}<div class="reason">{judgment.reason}</div>{/if}
  {#if judgment.options.length}
    <div class="buttons">
      {#each judgment.options as option (option)}
        <button class:primary={option === judgment.suggestion} onclick={() => answerJudgment(judgment.id, option)}>
          {option}
        </button>
      {/each}
    </div>
  {:else}
    <form onsubmit={sendTyped}>
      <input bind:value={typed} placeholder={judgment.suggestion} aria-label="Your answer" />
      <button class="primary" type="submit">Answer</button>
      <button type="button" onclick={() => answerJudgment(judgment.id, judgment.suggestion)}>Accept suggestion</button>
    </form>
  {/if}
</article>

<style>
  .judgment { border: 1px solid var(--accent); border-radius: 8px; padding: 8px 10px; display: flex; flex-direction: column; gap: 4px; font-size: 14px; }
  .reason { font-style: italic; }
  .buttons, form { display: flex; gap: 6px; margin-top: 4px; }
  input { flex: 1; min-width: 0; }
</style>
