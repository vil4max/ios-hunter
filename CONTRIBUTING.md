## Contributing

Thanks for your interest in contributing.

### What to contribute

- Fix broken collectors / parsing edge cases
- Add new company sources (Swift) or feeds (Python)
- CI improvements and reliability hardening

### Development

This repository is designed to run on **GitHub Actions**.

For local checks:

```bash
python3 -m pip install -r requirements.txt -r requirements-dev.txt
python3 -m pytest -q
python3 -c "from collector.companies import collect_all; from database.seen import load_seen; from integrations.notify import format_vacancy_message"
```

### Pull requests

- Keep changes focused and small
- Prefer incremental commits with clear messages (Conventional Commits)
- Do not commit secrets or personal credentials

### Reporting issues

Please include:

- Expected vs actual behavior
- Reproduction steps / logs
- Example URLs or minimal samples (without secrets)
