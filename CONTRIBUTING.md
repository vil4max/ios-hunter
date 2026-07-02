## Contributing

Thanks for your interest in contributing.

### What to contribute

- Fix broken collectors / parsing edge cases
- Add new company sources (Swift) or feeds (Python)
- Improve reports / GitHub Pages dashboard
- CI improvements and reliability hardening

### Development

This repository is designed to run on **GitHub Actions**.

For local checks:

- Python: `python3 -m pip install -r requirements.txt`
- Smoke check: `python3 -c "from collector.companies import collect_all; from ai.engine import create_analyzer; from parser.pipeline_steps import apply_job_change"`

### Pull requests

- Keep changes focused and small
- Prefer incremental commits with clear messages (Conventional Commits)
- Do not commit secrets or personal credentials
- If you change public artifacts (reports / website data), explain why

### Reporting issues

Please include:

- Expected vs actual behavior
- Reproduction steps / logs
- Example URLs or minimal samples (without secrets)
