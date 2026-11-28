# A session resumes one Referee conversation until End session

The harness saves the Referee conversation to the campaign folder as it happens, and resumes it after a server restart or a closed tab until the player clicks End session. Only a new session, or a resume that fails, starts a new conversation from `session_opening` and the vault. We chose this over a fresh conversation after every restart because the Referee then keeps everything from the session, and the saved file shows what the Referee saw when a session note goes wrong. The cost is a first turn after a long break with a cold prompt cache, which sends the whole conversation again at full price. The player accepted that cost, and Compact reduces it.

## Consequences

- **Conversation files.** Each conversation goes to `referee/conversations/` in the campaign folder, not to `~/.claude/projects/`. Files of closed sessions stay on disk for debugging and never load again.
- **Open and closed.** A session is open when its raw log exists. No other flag exists. The campaign screen, between the library and the table, shows "Resume session N" for an open session. Otherwise it shows "Start a new session" and "Start without recap".
- **Resume.** A resume reloads the chat history of the session and shows no recap.
- **Start.** "Start a new session" runs each owed write-up, oldest first, then opens the table with a "Session N starts" card from the engine and a recap turn. The card shows the map, area, HP, and conditions. The recap uses the current model and effort. It reads the previous session note and the records that it links, or the raw log of a session that has no note. The ADR 0005 digest comes after it.
- **The recap is not play.** It shows in the chat but does not go into the raw log. A session that holds only a recap stays closed, and End session has nothing to write up.
- **Close without write-up.** If the write-up turn fails, the error offers "Close without write-up". It starts the next session, and the engine records that the closed session owes a write-up. The owed write-up runs at the next start, before any play, so facts from the old session cannot overwrite newer records. If it fails again, the recap reads the raw log, and the write-up stays owed.
