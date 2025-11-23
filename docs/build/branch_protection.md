# Branch Protection Checklist

Set these status checks as required on the `main` branch so no code merges without passing the agents:

- Hygiene (`hygiene` workflow)
- Docs/API (`docs_api` workflow)
- Memorialization (`memorialization` workflow)
- Migrations (`migrations` workflow)
- Tests (`tests` workflow)
- Security (`security` workflow)
- Quality (`quality` workflow)
- Bundle PR report (`bundle-report` job in `report` workflow)
- Coverage report (`coverage` job in `coverage-report` workflow)

Notes:
- Nightly audit is informational and should not block PRs.
- If you rename workflows/jobs later, update this list.
