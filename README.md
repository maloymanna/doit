# doit

doit is a local agent that:
- Operates inside a controlled workspace
- Uses Playwright + Microsoft Edge to drive ChatGPT/LLM web UIs
- Reads/writes files with strict permissions and autonomy modes
- Uses plugins for capabilities like summarization and iterative loops
- Supports controlled autonomy levels (0, 1, 2)

Runtime state lives inside `.doit/` in your workspace directory.

## Quick start

1. Create a workspace directory.
2. Run: `doit init-workspace`
3. Edit `.doit/config.yaml` and `.doit/playwright_config.yaml`.
4. Use commands like:
```text
doit summarize-file path/to/file --project my_project
doit ralph-loop "prompt" --max-iterations 10 --completion-promise DONE
```


