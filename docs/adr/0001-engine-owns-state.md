# The engine owns mechanical state and dice; the Referee owns the story notes

The engine holds all mechanical state (HP, position, the map, clocks, inventory counts) and makes every roll. The Referee changes that state only through engine tools, and a click in the harness calls the same engine actions. The Referee writes the story freely as markdown notes in the campaign vault with file tools that reach only the vault. We split it this way because earlier Ironsworn play showed the AI running moves wrong and skipping bookkeeping, while a strict tool set for story notes would cut the Referee off from the free journaling that works well in the owner's Obsidian vaults.

## Consequences

- A fresh session starts from engine state plus the vault, so the Referee must write notes as play goes on.
- Every procedure needs engine code before the Referee can use it.
- Live trackers stay out of the notes. The engine writes a read-only state note so Obsidian still shows them.
