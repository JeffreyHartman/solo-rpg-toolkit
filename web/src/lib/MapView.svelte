<!-- Full-screen map layer: known areas, exits, and the party token. Drag pans, the wheel zooms. -->
<script lang="ts">
  import type { Area, EngineState } from './protocol'
  import { act, exploreActionFor, moveActionTo } from './socket.svelte'

  let { snapshot }: { snapshot: EngineState } = $props()

  const CELL = 32
  const DRAG_THRESHOLD = 4

  let view = $state({ x: 0, y: 0, k: 1 })
  let fitted = false
  let svg = $state<SVGSVGElement>()
  let drag: { x: number; y: number; vx: number; vy: number; moved: boolean } | null = null

  let areas = $derived(Object.entries(snapshot.map.areas))
  let known = $derived(areas.filter(([, a]) => a.known))
  let here = $derived(snapshot.map.areas[snapshot.party.area])

  const centre = (a: Area) => ({ x: (a.x + a.w / 2) * CELL, y: (a.y + a.h / 2) * CELL })

  const EXIT_OFFSET = 18

  // Where the line from the centre of `near` toward `to` crosses its wall.
  function wallPoint(near: Area, to: { x: number; y: number }) {
    const c = centre(near)
    const dx = to.x - c.x
    const dy = to.y - c.y
    const t = Math.min(dx ? (near.w * CELL) / 2 / Math.abs(dx) : Infinity, dy ? (near.h * CELL) / 2 / Math.abs(dy) : Infinity)
    const len = Math.hypot(dx, dy) || 1
    const wall = { x: c.x + dx * t, y: c.y + dy * t }
    return { wall, marker: { x: wall.x + (dx / len) * EXIT_OFFSET, y: wall.y + (dy / len) * EXIT_OFFSET } }
  }

  let links = $derived(
    snapshot.map.connections.flatMap((c) => {
      const a = snapshot.map.areas[c.a]
      const b = snapshot.map.areas[c.b]
      if (!a.known && !b.known) return []
      const [near, far, farId] = a.known ? [a, b, c.b] : [b, a, c.a]
      const { wall, marker } = wallPoint(near, centre(far))
      return [{ id: c.id, from: centre(near), to: centre(far), wall, marker, open: far.known, target: farId }]
    }),
  )

  const SIDE: Record<string, [number, number]> = { n: [0, -1], s: [0, 1], e: [1, 0], w: [-1, 0] }
  let openExits = $derived(
    (snapshot.map.open_exits ?? []).flatMap((e) => {
      const near = snapshot.map.areas[e.area]
      if (!near?.known) return []
      const [dx, dy] = SIDE[e.side]
      const c = centre(near)
      const wall = { x: c.x + (dx * near.w * CELL) / 2, y: c.y + (dy * near.h * CELL) / 2 }
      return [{ id: e.id, wall, marker: { x: wall.x + dx * EXIT_OFFSET, y: wall.y + dy * EXIT_OFFSET } }]
    }),
  )

  function explore(exit: string) {
    if (drag?.moved) return
    const action = exploreActionFor(exit)
    if (action) act(action.command)
  }

  $effect(() => {
    if (fitted || !svg || known.length === 0) return
    const xs = known.flatMap(([, a]) => [a.x, a.x + a.w])
    const ys = known.flatMap(([, a]) => [a.y, a.y + a.h])
    const box = svg.getBoundingClientRect()
    const cx = ((Math.min(...xs) + Math.max(...xs)) / 2) * CELL
    const cy = ((Math.min(...ys) + Math.max(...ys)) / 2) * CELL
    view = { x: box.width / 2 - cx, y: box.height / 2 - cy, k: 1 }
    fitted = true
  })

  function onpointerdown(e: PointerEvent) {
    drag = { x: e.clientX, y: e.clientY, vx: view.x, vy: view.y, moved: false }
  }
  function onpointermove(e: PointerEvent) {
    if (!drag) return
    const dx = e.clientX - drag.x
    const dy = e.clientY - drag.y
    if (Math.hypot(dx, dy) > DRAG_THRESHOLD) drag.moved = true
    if (drag.moved) view = { ...view, x: drag.vx + dx, y: drag.vy + dy }
  }
  function onpointerup() {
    setTimeout(() => (drag = null))
  }
  function onwheel(e: WheelEvent) {
    e.preventDefault()
    if (!svg) return
    const box = svg.getBoundingClientRect()
    const px = e.clientX - box.left
    const py = e.clientY - box.top
    const k = Math.min(4, Math.max(0.25, view.k * Math.exp(-e.deltaY * 0.0015)))
    view = { k, x: px - ((px - view.x) * k) / view.k, y: py - ((py - view.y) * k) / view.k }
  }
  function go(area: string) {
    if (drag?.moved) return
    const action = moveActionTo(area)
    if (action) act(action.command)
  }
</script>

<svg bind:this={svg} {onpointerdown} {onpointermove} {onpointerup} {onwheel} role="application" aria-label="Map">
  <g transform="translate({view.x} {view.y}) scale({view.k})">
    {#each links as l (l.id)}
      {#if l.open}<line x1={l.from.x} y1={l.from.y} x2={l.to.x} y2={l.to.y} class="link" />{/if}
    {/each}
    {#each known as [id, a] (id)}
      <g class="area" class:here={id === snapshot.party.area} class:reach={!!moveActionTo(id)} onclick={() => go(id)} role="button" tabindex="0" onkeydown={(e) => e.key === 'Enter' && go(id)}>
        <rect x={a.x * CELL} y={a.y * CELL} width={a.w * CELL} height={a.h * CELL} rx="3" />
        <text x={centre(a).x} y={centre(a).y + 4}>{a.name}</text>
      </g>
    {/each}
    {#each links.filter((l) => !l.open) as l (l.id)}
      <g class="exit" class:reach={!!(l.target && moveActionTo(l.target))} onclick={() => go(l.target)} role="button" tabindex="0" onkeydown={(e) => e.key === 'Enter' && go(l.target)}>
        <line x1={l.wall.x} y1={l.wall.y} x2={l.marker.x} y2={l.marker.y} class="link dashed" />
        <circle cx={l.marker.x} cy={l.marker.y} r="10" />
        <text x={l.marker.x} y={l.marker.y + 4}>?</text>
      </g>
    {/each}
    {#each openExits as o (o.id)}
      <g class="exit" class:reach={!!exploreActionFor(o.id)} onclick={() => explore(o.id)} role="button" tabindex="0" onkeydown={(e) => e.key === 'Enter' && explore(o.id)}>
        <line x1={o.wall.x} y1={o.wall.y} x2={o.marker.x} y2={o.marker.y} class="link dashed" />
        <circle cx={o.marker.x} cy={o.marker.y} r="10" />
        <text x={o.marker.x} y={o.marker.y + 4}>?</text>
      </g>
    {/each}
    {#if here}
      <circle class="party" cx={centre(here).x} cy={centre(here).y - 16} r="8" />
    {/if}
  </g>
</svg>

<style>
  svg { width: 100%; height: 100%; display: block; background: var(--fog); cursor: grab; touch-action: none; }
  text { fill: var(--ink-dim); font-size: 12px; text-anchor: middle; pointer-events: none; }
  .link { stroke: #c9a25e66; stroke-width: 4; }
  .link.dashed { stroke-dasharray: 4 4; }
  .area rect { fill: var(--room-known); stroke: #c9a25e88; stroke-width: 2; }
  .area.here rect { fill: #4a3a26; }
  .area.reach { cursor: pointer; }
  .area.reach:hover rect { stroke: var(--accent); }
  .exit circle { fill: var(--bg); stroke: #c9a25e88; stroke-width: 2; }
  .exit text { fill: var(--accent); font-weight: bold; }
  .exit.reach { cursor: pointer; }
  .exit.reach circle { stroke: var(--accent); filter: drop-shadow(0 0 4px #c9a25e); }
  .party { fill: var(--ink); stroke: var(--bg); stroke-width: 2; transition: cx 0.3s, cy 0.3s; }
</style>
