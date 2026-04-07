# Release Checklist

- Confirm the written spec and runtime behavior still match.
- Run the full test suite: `PYTHONPATH=src python3 -m unittest discover -s tests -v`
- Confirm example integrations still converge deterministically.
- Confirm package schemas and published schemas are aligned.
- Review README, architecture docs, and contributing guidance for outdated claims.
- Bump version in `pyproject.toml`.
- Tag the release and publish notes describing compatibility expectations.

