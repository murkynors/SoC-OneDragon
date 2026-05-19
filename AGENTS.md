# Agent Notes

- Reward popups are optional states. Handlers such as `dismiss_harvest_summary()` must only close a popup when it is detected, and callers must not assume the popup always appears.
- This is an in-game automation flow. Do not use Android/system Back for navigation, and do not blindly tap the top-left avatar area as a fallback. Return navigation should click the in-game `Icons/backButton.png` only when it is detected.
