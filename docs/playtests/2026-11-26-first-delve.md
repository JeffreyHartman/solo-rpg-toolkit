# Playtest 2026-11-26: first delve with the harness (v0.7.0)

Build: `v0.7.0` (PR #18). Campaign: `solo-harness demo`, with the Agent SDK Referee. Character: Brannoc, the demo character with no scores or gear.
Result: the party had one torch, the torch burned out, Brannoc left, and End session wrote `Sessions/Session 001 - A Short Torch.md`.

The owner's notes, verbatim:

```text
gameplay notes:
clicked search:
    the ref said "I searched the gatehouse..." - it sounds like its narratnig its work instead of responding as a gm. The 2nd paragraph sounds good, but it could be considered a tad long. the 3rd paragraph environment clues are pretty good, i like that.
    
    Here's another ref narrating like an agent instead of a gm frmo a later turn - "I checked your pack, Brannoc, and it's empty: no oil, no coin, nothing at all." That whole turn reveals this problem a bit more really, theres another paragraph where its respodning liek an agent: "There's also a problem out of character. The engine tracks your light, and none of my tools can add a new light source." - it probably reveals an issue which is good, so it was useful it said it..but it doesn't really belogn in teh gameplay - maybe stuff like that could be like hidden 'thinking' text? like we tell the agent it can include debug messages when it thinks there's an issue with the harness, but its hidden behind a click , similar to how smoe ai chat apps hide 'Reasoning' but you can cilck to show its thinking tokens.
the map:
    ref says ther is an arch to the east but i dont see that on the map? i am guessing because its a closed door? the map needs to make that clearer when we come back to the ui design
rules:
    i like inthe responses wehre it gives a rules source, like this one from the first turn - "Old-School Essentials Classic Fantasy, Adventures, p12-13" - idea, would be cool to make those clickable and it brings up markdown source in a new panel to read the rules. We have been working on a chat agent at work that does this and it's pretty effective. 
no page ref:
    related to the above, on this rule it did not cite the page source. "Old-School Essentials Classic Fantasy, Adventures, p12-13" - whats puting the page source citations in there, is the agent just encouraged to do it or is there some sort of harness mechanism that forces it to include it?
chat interface:
    it does not auto-scroll when new output is streaming when im al lteh way at the bottom. Most ai chat interfaces will auto scroll when all the awy at the bottom. this might have been deferred for the ui design
chat interface:
    input is one single line so i cant see what im typing when its long. Most chat interfaces will have line breaks and multiple lines showing and maybe give the dive more height to hold more lines when typing long information. This is also probably a #3 UI thing? I think what we need to do is have some research spikes for the agent to go explore popular and well made interfaces and copy usability patterns and the like. 
chat interface:
    It's hard to see where each turn happened, theres not erally any seperation. need to figure out better way t oseperate thigns. Also, i cant expand or move the dang thing and its annoyingly small, but im sure that aws deferred for #3.
```

Later points from the same conversation:

- Agents need a way to run the UI and take screenshots with the Playwright CLI, headless, to test their own UI work.
- A real start has a shopping step with starting gold, and does not start in an anonymous dungeon. The harness needs a full inventory.
- The first spec was a proof of concept. The next step is a roadmap in phases (wayfinder). The Augur (theaugur.app), an Ironsworn app, is a reference for a full-featured harness.

Answers found while triaging:

- Page citations come from the `source` field of each OSE table JSON. The engine copies it into the mechanics card, and the Referee repeats it. Nothing forces a citation, and sources built in code (for example the wandering check) have no page.
- The torch is a gap: the engine gives one 6-turn torch, inventory has no spare light, and no procedure lights one.
