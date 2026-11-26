<!-- Character creation: the player picks a class, a name and a description; the engine rolls the abilities. -->
<script lang="ts">
  import { createCharacter, game, OSE_CLASSES, say } from './socket.svelte'

  let characterClass = $state(OSE_CLASSES[0])
  let name = $state('')
  let description = $state('')

  function submit(event: SubmitEvent): void {
    event.preventDefault()
    createCharacter(characterClass, name, description)
  }
</script>

<form class="panel creation" onsubmit={submit}>
  <h3>Create your character</h3>
  <p class="dim">Abilities are rolled 3d6 in order by the engine.</p>
  <label>Class <select bind:value={characterClass}>{#each OSE_CLASSES as c (c)}<option>{c}</option>{/each}</select></label>
  <label>Name <input bind:value={name} /></label>
  <label>Description <textarea rows="3" bind:value={description}></textarea></label>
  <div class="row">
    <button type="button" disabled={game.refereeBusy}
      onclick={() => say(`Help me name and describe a ${characterClass}. Suggest a few names and a short description.`)}>
      Ask the Referee for ideas
    </button>
    <button class="primary" disabled={!name.trim()}>Roll character</button>
  </div>
</form>

<style>
  .creation { position: fixed; top: 12px; left: 50%; transform: translateX(-50%); width: min(420px, calc(100vw - 24px)); display: flex; flex-direction: column; gap: 6px; background: #17120df0; border: 1px solid var(--edge); border-radius: 10px; padding: 8px 12px; z-index: 2; }
  label { display: flex; flex-direction: column; }
  .row { display: flex; gap: 6px; justify-content: space-between; }
  h3 { margin: 0; }
</style>
