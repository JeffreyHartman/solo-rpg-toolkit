# Building a fog-of-war map from a module PDF

This note covers how to turn a published dungeon map into three things. The
first is a player viewer that reveals areas by id. The second is an exit table
for the referee. The third is a set of per-area crops. It assumes python3 with
Pillow and numpy, poppler's `pdftoppm`, `pdftotext` and `pdfimages`, and a
headless Chromium for checks.

The scripts named below are not in this repo. Their config holds one module's
coordinates, so they live with that campaign's key in `dungeon/map/build/`.
They are a working example of every step.

The build writes a stage directory that `tools/install_map.py` installs:

    stage/
    ├── viewer/      copied to map/: index.html, map.png, masks/, patches/,
    │                areas.js and areas.json (ids, kinds, bboxes, mask paths)
    └── referee/     merged into dungeon/map/: exits.json, crops/, build/

`map/index.html` ships with the template. The copy in a stage replaces it only
when the build changes the viewer.

## 1. Get the raster

1. Run `pdfimages -list` on the map pages. When the map is one embedded image
   per page, extract it with `pdfimages -png`. That gives the native resolution
   without the page's text overlays, which on quick-reference maps often carry
   key text. Use `pdftoppm -r 150` or higher only when the map is vector art.
2. When a map spans two pages, join the images. Find the overlap by comparing
   the last columns of the left image with the first column of the right one,
   and the best match gives the join column. Check that grid lines continue
   across the seam.
3. Work out the scale from the grid, for example 50 px per 10-foot square.
   Check it against one room whose size you know.

## 2. Find the labels

- Run `pdftotext -bbox` on the pages first. When room numbers are PDF text,
  their coordinates come for free (convert points to pixels with the image's
  ppi and page offset).
- When the numbers are baked into the image, read them by eye. `zoom.py` in the
  build folder renders an enlarged crop with a coordinate grid. Record a seed
  point on bare floor next to each label, not on the label itself, because
  letter strokes count as wall.
- An id printed twice (two rooms with one number) gets two seeds.

## 3. Flood the floor

- Wall = gray below a threshold (about 110 on a white-floored map). Grid dashes
  can be darker than you expect, so sample them first. Dashes are broken
  lines, so floor still connects around them.
- Close the outside first. Draw barrier lines where the map runs off the page,
  where an entrance opens onto blank paper, and where wall lines fade out (for
  example stair ends). Then run the leak check (`ext.py`). It floods from the
  image corners and reports every seed it reaches. Hatched rock is white
  between strokes, so it usually connects to the outside, and any gap in a
  wall leaks.
- Split connected floor between areas with cut lines across each opening.
  The build runs a multi-source flood (breadth-first from all seeds at once),
  so any pair of seeds you did not cut ends up split along the line of equal
  distance. That is acceptable in open caves and poor elsewhere.
- Door symbols drawn as closed rectangles stop the flood by themselves. Their
  interiors become small enclosed components. Add each one to every area within
  a few pixels, so a door shows from both sides. Select them by size and
  rectangularity. Doors drawn at 45 degrees fail the rectangularity test, so
  list them by hand.
- Fill holes (letter counters, feature symbols), dilate 4-6 px so walls show,
  and save one alpha mask per area cropped to its bounding box.
- Unnumbered corridors get their own ids (c1, c2, ...) so each one can be
  revealed on its own.

## 4. Hand fallbacks

Use rectangles for things a flood cannot isolate:

- doors that carry their own number
- passages drawn through hatched rock
- secret-door spots

Keep them in the same config as the seeds so a rebuild reproduces them.

## 5. Hide GM-only marks

Secret-door symbols, dotted secret-passage lines and similar marks must not
show when the area beside them is revealed.

- Do not paint new lines over them. Drawn lines come out darker and thicker
  than the art's own antialiased walls, and players notice.
- Instead, clone real pixels over the mark. For the rows that carry the wall
  stroke, copy a stretch of the same wall a grid square along it (a shift of
  one grid square keeps dashes in phase). For the floor on either side, copy
  from the same room or corridor shifted along its length. That brings the side
  walls with it. Split the patch into bands by source, extend each band over
  any wall the mark had covered, and feather only the outer 3 px, except where
  the clone differs strongly from the original.
- Keep clone sources clear of room numbers and other marks.
- Save a crop of the original under each patch. The viewer draws it back when
  the patch's owner id (the secret door's id) is revealed.
- Check with `compare.py` at 1x, 2x and 4x, and view the result: each row shows
  the original, the patch and a plain stretch of wall. Iterate until the patch
  cannot be told apart from the plain wall.
- Floods must still treat a hidden secret door as wall. A cloned wall is thin,
  so check that flood regions do not leak through it.

## 6. Exits from adjacency

`exits_build.py` finds exits from four kinds of evidence:

- a cut line gives an opening. Its width is the run of floor along the cut, not
  the cut's own length, which overshoots into the walls
- two flood regions touching with no cut between them give a cave-style
  opening. Mark these low confidence and split them into separate contacts,
  because two caves can touch in more than one place
- a door interior touching two areas gives a door. If the door has its own id,
  record it as `via`
- a secret-door patch gives a secret door between the areas on either side,
  marked `secret`

Add the rest by hand: exits to the outside, off-map ends, stairs, marked secret
passages, and doors merged into a small room's flood. Compute the compass wall
from the exit point and the bounding box of the part of the area that holds
it. Then check everything on `exits_check.png` by eye.

The exit list also needs a sanity check. Look for areas with no exits, exits
to nowhere (outside or off-map are fine when they are real), and exits with no
return.

## 7. Referee crops

For each id, crop the unpatched map around the mask bounding box with a 40 px
margin and outline the mask in a bright colour. The referee opens these when
the key text and the exit table disagree.

## 8. Verify

- Run the leak check after every change to barriers, cuts, thickening or
  patches.
- Take headless screenshots: `chromium --headless=new --screenshot=out.png
  --window-size=1400,900 --virtual-time-budget=6000 file://.../index.html`.
  Take one with the demo reveal state, one with everything revealed (every part
  of the map should be covered, with no dark door interiors), and a few sets
  of neighbouring areas to check that masks follow the walls.
- Screenshot every hidden mark twice at about 1:1 scale, once with its
  neighbours revealed and once with its own id revealed as well. The first
  should show plain wall and the second the original mark. Diff the two
  screenshots to find the spots.
- Check that the viewer still loads when the reveal file is missing.

## What went wrong last time

- **Rough cave walls leak.** Rock bumps along a cave edge leave pixel gaps, and
  the flood spills into the enclosed rock beyond. Dilating walls by 2 px
  inside a box around the caves fixed it. Keep that box away from doors, or
  the door interiors shrink and drop out of the masks.
- **Enclosed rock pockets fill up.** Hatched rock that the outside cannot reach
  still fills from any room with a gap. When an area comes out oversized,
  trace the shortest path from its seed into the pocket to find the gap.
- **Labels sit inside neighbouring areas.** A door's or feature's number is
  often printed in the corridor beside it, so revealing the corridor shows the
  number. The fix is a patch owned by that id; list it as a known issue
  otherwise.
- **Clone sources hit labels.** The first secret-door patches copied fragments
  of a nearby room number into a corridor.
- **Hidden marks had covered wall ends.** A secret-door symbol hid the last few
  pixels of the corridor walls beside it, so the first clones left gaps at the
  corners. Extend the clone band across those walls.
- **Walls fade out at stairs.** Stair hatching replaces solid wall lines, so the
  flood leaves through the stair end. Close it with barriers.
- **Features overlap cut lines.** A cut drawn straight across an opening beside
  an angled wall also crosses floor past the opening, which inflates the width.
- **Nearest-seed splits are approximate.** They are fine for caves but put
  boundaries mid-corridor, so give corridors their own seeds and cuts.
