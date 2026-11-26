<!-- Layout from the ui-shell prototype, variant C: the map fills the screen and panels float over it. -->
<script lang="ts">
  import CharacterCreation from './lib/CharacterCreation.svelte'
  import CharacterPanel from './lib/CharacterPanel.svelte'
  import CombatPanel from './lib/CombatPanel.svelte'
  import ChatPanel from './lib/ChatPanel.svelte'
  import ContextDrawer from './lib/ContextDrawer.svelte'
  import JudgmentCard from './lib/JudgmentCard.svelte'
  import LibraryScreen from './lib/LibraryScreen.svelte'
  import MapView from './lib/MapView.svelte'
  import ProposalCard from './lib/ProposalCard.svelte'
  import SettingsMenu from './lib/SettingsMenu.svelte'
  import TopBar from './lib/TopBar.svelte'
  import { act, game, listCampaigns } from './lib/socket.svelte'

  let settingsOpen = $state(false)
  let drawerOpen = $state(false)
  let pending = $derived(game.state?.proposals?.pending ?? [])
  let judgments = $derived(game.state?.judgments?.pending ?? [])

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
  {#if game.state.combat}
    <div class="panel combat"><CombatPanel combat={game.state.combat} /></div>
  {/if}
  <div class="panel log"><ChatPanel /></div>
  <div class="panel top">
    <TopBar ondrawer={() => (drawerOpen = !drawerOpen)} onsettings={() => (settingsOpen = !settingsOpen)} />
  </div>
  {#if settingsOpen}
    <div class="panel settings"><SettingsMenu onclose={() => (settingsOpen = false)} /></div>
  {/if}
  {#if drawerOpen}
    <div class="panel drawer"><ContextDrawer onclose={() => (drawerOpen = false)} /></div>
  {/if}
  <div class="dock">
  {#if pending.length || judgments.length}
    <div class="panel proposals">
      {#each judgments as judgment (judgment.id)}<JudgmentCard {judgment} />{/each}
      {#each pending as proposal (proposal.id)}<ProposalCard {proposal} />{/each}
    </div>
  {/if}
  <nav class="panel actions">
    <button onclick={listCampaigns}>Campaigns</button>
    {#each game.actions as a (a.id)}
      <button onclick={() => act(a.command)}>{a.label}</button>
    {/each}
  </nav>
  </div>
  {#if game.state.party.members.length === 0}<CharacterCreation />{/if}
{:else if !game.library}
  <p class="waiting dim">Connecting to the harness…</p>
{/if}
{#if !game.connected && game.state}<div class="panel offline">Disconnected, retrying…</div>{/if}

<style>
  .map { position: fixed; inset: 0; }
  .panel { position: fixed; background: #17120ddd; border: 1px solid var(--edge); border-radius: 10px; padding: 8px 12px; }
  .party { top: 12px; left: 12px; }
  .combat { top: 64px; left: 50%; transform: translateX(-50%); min-width: 220px; max-width: calc(100vw - 24px); }
  .log { left: 12px; bottom: 12px; width: min(460px, calc(100vw - 24px)); height: 45vh; font-size: 14px; }
  .dock { position: fixed; right: 12px; bottom: 12px; display: flex; flex-direction: column; align-items: flex-end; gap: 8px; max-width: calc(100vw - 24px); }
  .dock > .panel { position: static; }
  .actions { display: flex; flex-wrap: wrap; gap: 6px; max-width: min(480px, calc(100vw - 24px)); }
  .offline { top: 64px; left: 12px; color: var(--warn); }
  .top { top: 12px; right: 12px; max-width: calc(100vw - 24px); z-index: 3; }
  .settings { top: 72px; right: 12px; width: min(340px, calc(100vw - 24px)); z-index: 2; }
  .drawer { top: 72px; right: 12px; bottom: 12px; width: min(520px, calc(100vw - 24px)); z-index: 2; }
  .proposals { width: min(380px, calc(100vw - 24px)); display: flex; flex-direction: column; gap: 8px; max-height: 50vh; overflow-y: auto; }
  .waiting { padding: 24px; }
</style>
