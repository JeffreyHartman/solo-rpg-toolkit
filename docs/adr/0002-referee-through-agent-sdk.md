# The Referee runs through the Agent SDK on the player's own Claude plan

The default Referee adapter drives the Claude Agent SDK, signed in with the player's own Claude subscription, and gives it only engine tools. A second adapter calls OpenRouter with the player's own key. We chose this over the Claude API because the owner does not want per-token cost, and Anthropic permits an individual to sign in to the unmodified Claude Code binary with their own plan. Anthropic does not permit an app to route other people through one person's plan, so every player who uses the harness signs in with their own credentials.

## Consequences

- Plan usage limits bound session length, so the context budget is a player setting.
- The Agent SDK must load no user or project Claude Code settings (`setting_sources=[]`) and must use a custom system prompt, so engineering skills and instructions stay out of the Referee's context.
