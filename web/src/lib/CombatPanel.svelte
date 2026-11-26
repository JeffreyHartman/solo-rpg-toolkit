<!-- The foes of the current fight with hit points and status. App.svelte shows it only while combat is on. -->
<script lang="ts">
  import type { Combat } from './protocol'

  let { combat }: { combat: Combat } = $props()
</script>

<b>Combat</b> <span class="dim">round {combat.round} · {combat.phase === 'party' ? 'your turn' : 'foes act'}</span>
<ul>
  {#each combat.monsters as m (m.id)}
    <li class:gone={m.status !== 'alive'}>
      {m.name} <span class="dim">{m.id}</span>
      · HP {m.hp}/{m.max_hp}{#if m.status !== 'alive'} · {m.status}{/if}
    </li>
  {/each}
</ul>

<style>
  ul { margin: 4px 0 0; padding: 0; list-style: none; }
  .gone { text-decoration: line-through; opacity: 0.6; }
</style>
