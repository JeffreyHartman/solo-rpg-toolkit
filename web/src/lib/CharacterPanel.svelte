<!-- The party: one sheet per member, with tabs when the party has more than one. -->
<script lang="ts">
  import type { Member } from './protocol'

  let { members }: { members: Member[] } = $props()
  let selected = $state(0)
  let member = $derived(members[Math.min(selected, members.length - 1)])
</script>

{#if members.length > 1}
  <div class="tabs" role="tablist">
    {#each members as m, i (m.name)}
      <button role="tab" aria-selected={i === selected} class:primary={i === selected} onclick={() => (selected = i)}>{m.name}</button>
    {/each}
  </div>
{/if}
{#if member}
  <b>{member.name}</b>
  {#if member.class}<span class="dim"> {member.class}{member.level ? ` ${member.level}` : ''}</span>{/if}
  {#if member.hp !== undefined}<div>HP {member.hp}{member.max_hp !== undefined ? `/${member.max_hp}` : ''}</div>{/if}
  {#if member.abilities}
    <div class="dim">{Object.entries(member.abilities).map(([a, v]) => `${a} ${v}`).join(' · ')}</div>
  {/if}
  {#if member.description}<div class="dim">{member.description}</div>{/if}
{/if}

<style>
  .tabs { display: flex; gap: 4px; margin-bottom: 4px; }
</style>
