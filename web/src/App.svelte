<!-- Layout from the ui-shell prototype, variant C: the map fills the screen and panels float over it. -->
<script lang="ts">
  import CharacterCreation from './lib/CharacterCreation.svelte'
  import CharacterPanel from './lib/CharacterPanel.svelte'
  import ChatPanel from './lib/ChatPanel.svelte'
  import LibraryScreen from './lib/LibraryScreen.svelte'
  import MapView from './lib/MapView.svelte'
  import { act, game, listCampaigns } from './lib/socket.svelte'

  let light = $derived(
    game.state?.dungeon
      ? game.state.dungeon.light.map((l) => `${l.kind} ${l.turns_left}`).join(', ') || 'darkness'
      : '',
  )
  let here = $derived(game.state ? game.state.map.areas[game.state.party.area] : null)
</script>

<LibraryScreen />
{#if game.state && !game.library}
  <div class="map"><MapView snapshot={game.state} /></div>
  <div class="panel party">
    <CharacterPanel members={game.state.party.members} />
    <div class="dim">{here?.name} · session {game.state.session}</div>
    {#if game.state.dungeon}
      <div class="dim">Turn {game.state.dungeon.turn} · Light: {light}</div>
    {/if}
  </div>
  <div class="panel log"><ChatPanel /></div>
  {#if game.state.party.members.length === 0}<CharacterCreation />{/if}
  <nav class="panel actions">
    <button onclick={listCampaigns}>Campaigns</button>
    {#each game.actions as a (a.id)}
      <button onclick={() => act(a.command)}>{a.label}</button>
    {/each}
  </nav>
{:else if !game.library}
  <p class="waiting dim">Connecting to the harness…</p>
{/if}
{#if !game.connected && game.state}<div class="panel offline">Disconnected, retrying…</div>{/if}

<style>
  .map { position: fixed; inset: 0; }
  .panel { position: fixed; background: #17120ddd; border: 1px solid var(--edge); border-radius: 10px; padding: 8px 12px; }
  .party { top: 12px; left: 12px; }
  .log { left: 12px; bottom: 12px; width: min(460px, calc(100vw - 24px)); height: 45vh; font-size: 14px; }
  .actions { right: 12px; bottom: 12px; display: flex; flex-wrap: wrap; gap: 6px; max-width: min(480px, calc(100vw - 24px)); }
  .offline { top: 12px; right: 12px; color: var(--warn); }
  .waiting { padding: 24px; }
</style>
