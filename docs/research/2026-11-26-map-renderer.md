# Map renderer for the table

Date: 2026-11-26

Ticket: #42. Map: #40. Prototype that confirms the result: #48.

## Question

Which renderer draws the phase 2 map in the harness? The choices are:

- SVG in Svelte. `web/src/lib/MapView.svelte` uses it now.
- A 2D canvas or WebGL library, for example PixiJS or Konva.
- An open-source map component, for example Leaflet.

In phase 2, the renderer must do these tasks:

- Pan and zoom over a map of about 50 areas in a LAN browser.
- Draw a styled dungeon from area shapes: floor, walls, doors, and closed exits.
- Show an image file as the map background. Fog hides the image, and the engine reveals it area by area from masks or polygons.
- Show tokens and let the player drag them. A drop lands in an area.

In phase 7, the renderer must take a grid, walls, line of sight, and dynamic light on the same coordinates.

## Method

- I read the official docs, the npm metadata, and the GitHub repositories and licenses of each candidate. Each claim has a source in the list at the end.
- I bundled a small use of each library with esbuild (minify, ESM) and measured the gzip size. The use was: one image, one polygon, one mask, and pan or drag.
- I drew the same fog test with SVG, Konva, and PixiJS in Playwright 1.61.0 headless Chromium (149.0.7827.55). The test is a green floor, a black fog layer, and one revealed square. I read one pixel inside the square and one pixel outside it.

The test files are throwaway. They are not in the repo.

## Current renderer

`MapView.svelte` draws an SVG with one `<g transform>` for pan and zoom. Each known area is a `<rect>` in grid cells (`CELL = 32`). Exits are lines and circles, and the party token is a circle. Pointer events pan the view, and the wheel zooms it. Each area and exit is a DOM element with `role="button"`, a CSS class, and an `onclick` handler. The protocol gives each area `x`, `y`, `w`, `h` in cells (`web/src/lib/protocol.ts`).

`docs/fog-map.md` already describes a build that writes one alpha mask PNG per area, cropped to the bounding box, and a viewer that reveals areas by id. Each renderer below can use those masks.

The screenshot spec (`web/e2e/screenshots.spec.ts`) waits for the text "Gatehouse" and takes a page screenshot. It uses the default Playwright Chromium with no GPU flags.

## Candidates

### SVG in Svelte (current)

- **License.** No library. The harness owns the code.
- **Bundle size.** 0 KB added.
- **Svelte 5 fit.** Native. Svelte compiles SVG elements like other elements. Runes, `{#each}`, CSS classes, and event attributes work with no wrapper.
- **Fog masks.** An SVG `<mask>` uses the luminance of its content. White shows the masked element, and black hides it [MDN-MASK]. A fog `<rect>` takes a mask with a white rectangle and one black `<image>` or `<polygon>` for each revealed area. The per-area alpha PNGs from `docs/fog-map.md` go in as `<image>` elements.
- **Headless screenshots.** The fog test passed: inside `0,255,0`, outside `0,0,0`. SVG needs no WebGL and no GPU flag.
- **Cost to move.** None. Phase 2 adds an `<image>` background, area polygons or paths, a mask, and token drag to the existing component.
- **Phase 7.** A grid is a `<pattern>`. Walls are lines. A line-of-sight polygon is one `<polygon>` in the mask. The visibility math is plain TypeScript and does not depend on the renderer. Soft dynamic light needs gradients, blend modes, or filters. SVG filters run on the CPU, so many moving lights are the weak point of SVG.

### Konva (Canvas 2D)

- **License.** MIT. The LICENSE file says "MIT License" [KONVA-LIC]. GitHub shows `NOASSERTION` because the file also names the older KineticJS copyright.
- **Bundle size.** Measured: 62 KB gzip with the full `konva` import. 37 KB gzip with `konva/lib/Core` and only `Image` and `Line`.
- **Svelte 5 fit.** `svelte-konva` 1.0.1 (MIT) has the peer dependency `svelte ^5.0.0` and `konva 8 - 10` [NPM-SK]. Its README maps Svelte 5 to svelte-konva v1. It says the library is "client-side only". Events are callback props named `on{konva event name}` [SK-README]. The repository has 130 stars.
- **Fog masks.** Draw a black rectangle on a fog layer. Then draw each revealed shape on the same layer with `globalCompositeOperation: 'destination-out'`. The fog test passed: inside `0,255,0`, outside `0,0,0`.
- **Headless screenshots.** Canvas 2D needs no GPU. The test passed with and without `--enable-unsafe-swiftshader`.
- **Cost to move.** Medium. `MapView.svelte` becomes a Stage with layers. Areas and exits stop being DOM elements, so keyboard focus, `role="button"`, and CSS hover go away. The harness must rebuild them. Playwright `getByText` does not find canvas text, so the screenshot spec needs a new wait signal.
- **Phase 7.** Konva draws every node on a layer, also nodes outside the stage. Each layer is a separate canvas, and Konva warns above five layers [KONVA-PERF]. Light with composite operations runs on the CPU. Owlbear Rodeo 1.0 (legacy) used `react-konva` for a full VTT [OBR-PKG].

### PixiJS (WebGL or WebGPU)

- **License.** MIT [PIXI-REPO]. The repository has 48.9k stars and had a release on 2026-11-26 (8.23.0).
- **Bundle size.** Measured: 179 KB gzip for all chunks of a small use (23 chunks). The WebGL and WebGPU renderers are separate chunks, and the browser loads only one path. With `pixi-viewport` 7.0.3 (MIT) for pan and zoom: 191 KB gzip.
- **Svelte 5 fit.** `svelte-pixi` 8.0.1 (MIT) has the peer dependencies `svelte >=4.0.0 || >=5.0.0` and `pixi.js ^8.6.5` [NPM-SP]. Its docs have an "Upgrading to Svelte 5" page. It has 153 stars, and its last push was 2025-12-22. The harness can also call PixiJS directly from an `$effect` with no wrapper.
- **Fog masks.** A `Graphics` or a `Sprite` can be a mask. `setMask({ mask, inverse: true })` "renders everything outside the mask" [PIXI-SCENE]. Since v8.18.0, `setMask` takes `channel: 'alpha'` for an alpha PNG mask [PIXI-JUNE]. One object takes one mask only [PIXI-SCENE]. The fog test with an inverse `Graphics` mask passed: inside `0,255,0`, outside `0,0,0`.
- **Headless screenshots.** The test passed with the `webgl` and the `webgpu` preference. With `webgpu`, PixiJS fell back to WebGL. The WebGL renderer in headless Chromium was "ANGLE (Google, Vulkan 1.3.0 (SwiftShader Device (Subzero)))". The Chromium docs say that "WebGL context creation will soon fail instead of falling back to SwiftShader". The opt-in is `--enable-unsafe-swiftshader`, and the docs say it is "not intended for running untrusted content" [CR-SWS]. Thus a PixiJS map needs that flag in `playwright.config.ts` to keep screenshots stable.
- **Cost to move.** High. All of `MapView.svelte` becomes scene objects. The DOM accessibility and the `getByText` wait go away, as with Konva. The harness also adds about 180 KB gzip.
- **Phase 7.** Best fit. Foundry VTT says its canvas "uses the PixiJS library", and its CanvasVisibility group is "responsible for dynamic vision, lighting, and fog of war" [FVTT-API]. Shaders and blend modes run on the GPU.

### Leaflet (map component)

- **License.** BSD-2-Clause [LEAFLET-REPO]. The `latest` tag is 1.9.4. Version 2 is in beta (`2.0.0-beta.5`).
- **Bundle size.** Measured: 43 KB gzip for a map, one `imageOverlay`, one polygon, and one draggable marker. The CSS file is extra.
- **Svelte 5 fit.** No official Svelte wrapper. The harness calls Leaflet from an `$effect` and syncs state by hand.
- **Fog masks.** No mask feature. The tutorial uses `CRS.Simple` for "big scanned images, such as game maps" [LEAFLET-CRS]. Fog needs a custom SVG or canvas layer on top. Then Leaflet adds pan, zoom, and markers only.
- **Headless screenshots.** Leaflet draws vectors as SVG by default, so no GPU is necessary. Not tested here.
- **Cost to move.** Medium. Leaflet uses `[y, x]` coordinates and its own zoom levels. Leaflet markers are draggable [LEAFLET-REF].
- **Phase 7.** Weak. Leaflet has no lighting or vision. A grid, walls, and light are custom layers.

### VTT components (study only)

- **Owlbear Rodeo legacy.** It uses `konva` 8.3.5 and `react-konva` [OBR-PKG]. It has no license file. The README says "This project is for **personal** use only" and "This code won't be maintained or supported by us" [OBR-README]. Do not copy code.
- **dungeon-revealer.** ISC license [DR-REPO]. It uses `three` and `react-three-fiber` (WebGL) [DR-PKG]. `src/map-view.tsx` draws the fog into a 2D canvas, puts it on a `CanvasTexture`, and shows it on a mesh over the map image [DR-SRC]. This pattern works in any renderer: keep one fog bitmap and update it when an area is revealed.
- **Foundry VTT.** Proprietary. PixiJS canvas with separate layers for walls, lighting, and visibility [FVTT-API]. Reference only, as #40 says.

## Comparison

| | SVG in Svelte | Konva | PixiJS | Leaflet |
|---|---|---|---|---|
| License | none (own code) | MIT | MIT | BSD-2-Clause |
| Added size, gzip (measured) | 0 KB | 37 to 62 KB | 179 KB (all chunks) | 43 KB + CSS |
| Svelte 5 fit | native | `svelte-konva` 1.0.1 (Svelte 5) | `svelte-pixi` 8.0.1, or direct | none, direct calls |
| Fog masks | `<mask>` with `<image>` or `<polygon>` | `destination-out` on a fog layer | inverse `setMask`, alpha channel | no feature, custom layer |
| Headless screenshot (tested) | pass, no flags | pass, no flags | pass on SwiftShader; flag needed later | not tested |
| DOM text and a11y | kept | lost | lost | partly (SVG panes) |
| Cost to move from current SVG | none | medium | high | medium |
| Phase 7 grid and walls | good (`<pattern>`, lines) | good | good | custom |
| Phase 7 line of sight | polygon in mask; math in TS | polygon; math in TS | polygon or shader; math in TS | custom |
| Phase 7 dynamic light | weak (CPU filters) | fair (CPU composite) | strong (GPU) | none |

## Recommendation

Keep SVG in Svelte for phase 2. Put the map coordinates (units and an optional grid size) in the map model, not in the renderer.

Reasons:

1. Phase 2 needs about 50 areas, one image, area masks, and a few tokens. SVG does all of these with no new dependency.
2. The current component, its DOM tests, its accessibility, and the screenshot spec stay. The fog test passed headless with no GPU flag.
3. Every phase 2 fog source works in SVG: the per-area alpha PNGs from `docs/fog-map.md` and the area polygons.
4. The phase 7 risk is dynamic light, not grid, walls, or line of sight. Visibility math is renderer-free TypeScript. If SVG light is too slow, phase 7 adds a PixiJS canvas layer for light only, on the same coordinates, under the SVG. The save format does not change.

Do not use Leaflet. It adds pan and zoom but no fog and no light. Do not use Konva. It costs the DOM and gives no GPU path for phase 7.

## What prototype #48 must test

1. **Load.** A background image of about 4000 x 3000 px and 50 areas, each with an alpha mask PNG. Measure the time to the first frame.
2. **Pan and zoom.** Measure the frame time during a drag and a wheel zoom from 0.25x to 4x. Test on a LAN laptop and on a tablet. The target is less than 16 ms for each frame.
3. **Reveal.** Reveal one area and then 10 areas in one turn. Measure the time to the next frame. Check the mask edges at 4x for seams and dark door gaps.
4. **Token drag.** Drag the party token and drop it. Find the target area by a point-in-polygon test in map units, not by the DOM element under the pointer. Check that a drop on a hidden area or on a wall is refused.
5. **Screenshots.** Run `npm run screenshots` with the image map. Check that the screenshot waits for the image `load` event, not only for text.
6. **Phase 7 spike.** Compute a visibility polygon from about 200 wall segments on each token move, and use it as one mask polygon. Measure the frame time. Then draw 3 soft radial lights with blend modes. If the frame time is more than 16 ms, record that phase 7 needs a PixiJS light layer.

## Sources

- [MDN-MASK] MDN, `<mask>`: https://developer.mozilla.org/en-US/docs/Web/SVG/Reference/Element/mask
- [KONVA-LIC] Konva LICENSE: https://github.com/konvajs/konva/blob/master/LICENSE
- [KONVA-PERF] Konva, All performance tips: https://konvajs.org/docs/performance/All_Performance_Tips.html
- [NPM-SK] npm, svelte-konva 1.0.1: https://www.npmjs.com/package/svelte-konva
- [SK-README] svelte-konva README: https://github.com/konvajs/svelte-konva
- [PIXI-REPO] PixiJS repository: https://github.com/pixijs/pixijs
- [PIXI-SCENE] PixiJS v8 guide, Scene objects (masking): https://pixijs.com/8.x/guides/components/scene-objects
- [PIXI-JUNE] PixiJS blog, June 2026 update (`setMask` channel option): https://pixijs.com/blog/june-2026
- [NPM-SP] npm, svelte-pixi 8.0.1: https://www.npmjs.com/package/svelte-pixi
- [CR-SWS] Chromium docs, SwiftShader: https://chromium.googlesource.com/chromium/src/+/main/docs/gpu/swiftshader.md
- [FVTT-API] Foundry VTT API docs: https://foundryvtt.com/api/
- [LEAFLET-REPO] Leaflet repository: https://github.com/Leaflet/Leaflet
- [LEAFLET-CRS] Leaflet tutorial, Non-geographical maps: https://github.com/Leaflet/Leaflet/blob/main/docs/examples/crs-simple/index.md
- [LEAFLET-REF] Leaflet API reference, Marker `draggable`: https://leafletjs.com/reference.html
- [OBR-PKG] Owlbear Rodeo legacy, package.json: https://github.com/owlbear-rodeo/owlbear-rodeo-legacy/blob/main/package.json
- [OBR-README] Owlbear Rodeo legacy README: https://github.com/owlbear-rodeo/owlbear-rodeo-legacy
- [DR-REPO] dungeon-revealer repository (ISC): https://github.com/dungeon-revealer/dungeon-revealer
- [DR-PKG] dungeon-revealer package.json: https://github.com/dungeon-revealer/dungeon-revealer/blob/master/package.json
- [DR-SRC] dungeon-revealer `src/map-view.tsx`: https://github.com/dungeon-revealer/dungeon-revealer/blob/master/src/map-view.tsx
