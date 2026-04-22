# Panel Skill

Harness skill that allows easy communication with Companion Panel API v1.

Simply drop it as a skill in your harness of choice, create `.env` file inside of it, add your `PANEL_API_KEY` and start using right away.

Useful first-time commands:
- `/panel discover`: See what panel options you have at your disposal
- `/panel help <question>`: Ask for the best panel option to use with your problem
- `/panel setup`: Create initial panel setup for your current working project

> [!NOTE]
> Skill's script might result in long-polling loops (due to longer panel options like discussion), thus running requests for the panel is recommended to be specified as a background task. Claude Code should do it automatically, not tested in other harnesses.
