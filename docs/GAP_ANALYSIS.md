# Selenite Gap Analysis & Remediation Plan

## Overview
This document enumerates functional, technical, operational, and quality gaps remaining after completion of Increment 20. It provides prioritized remediation actions toward production robustness.

## Priority Legend
- P0: Critical for reliability/security before wider use
- P1: High impact; should be addressed in near-term (next sprint)
- P2: Medium; improves maintainability/quality
- P3: Long-term / strategic enhancement

## 1. Functional Gaps
| Gap | Impact | Priority | Remediation |
|-----|--------|----------|-------------|
| Frontend actions use placeholders (upload, restart, delete, tag CRUD, settings save) | User cannot persist real changes | P0 | Implement data layer with fetch wrappers; connect to API_CONTRACTS endpoints; add error handling & toast feedback |
| Missing transcript download formats integration (UI triggers without backend verification) | Export may fail silently | P1 | Verify backend export endpoints and wire responses; add failure toasts |
| No transcript editing UX | User cannot correct transcription errors | P3 | Add editable transcript component with diff + save endpoint |
| No batch upload | Slower workflow for multiple files | P3 | Extend upload modal for multi-file queueing |

## 2. Testing Gaps
| Gap | Impact | Priority | Remediation |
|-----|--------|----------|-------------|
| Frontend tests not executed (runner stability issue) | Unknown regression risk | P0 | Fix test harness; run all 104 tests; resolve hangs (investigate Vitest config, dependency versions) |
| Missing integration/E2E tests (Increment 19 skipped) | Critical workflow unverified | P0 | Introduce Playwright suite: login, upload, progress, completion, export, tag management |
| No coverage reporting enforced | Hard to measure quality gates compliance | P1 | Add coverage scripts (pytest --cov, vitest --coverage) + CI thresholds |
| No performance benchmarking tests | Unknown scaling characteristics | P2 | Create synthetic transcription load tests with different models |

## 3. Security & Auth Gaps
| Gap | Impact | Priority | Remediation |
|-----|--------|----------|-------------|
| No rate limiting / brute force protection | Credential stuffing risk | P0 | Add FastAPI limiter middleware (e.g., slowapi) for auth endpoints |
| No password complexity / rotation policy | Weak credential hygiene | P1 | Enforce length/entropy via validation rules; document rotation guidance |
| No account lockout on repeated failures | Susceptible to brute force | P1 | Track failed attempts; temporary lock after N failures |
| No JWT refresh / short-lived access tokens | Risk if token leaked | P2 | Implement refresh token pair, shorter access token TTL |
| Logging not structured / no audit trail | Hard incident investigation | P2 | Add structured JSON logging (user actions, admin changes) |
| No CSRF strategy for non-REST form posts (if expanded) | Future risk if forms added | P3 | Evaluate SameSite cookies & CSRF tokens when introducing forms |

## 4. Observability & Monitoring Gaps
| Gap | Impact | Priority | Remediation |
|-----|--------|----------|-------------|
| No metrics instrumentation (Prometheus) | Hard to monitor performance | P1 | Add prometheus-fastapi-instrumentator; expose /metrics; add dashboards |
| No centralized logs or rotation policy | Disk bloat & lost context | P1 | Implement log rotation (logrotate) + structured logs |
| No alerting thresholds defined | Delayed issue detection | P2 | Define error rate, latency, queue depth alerts |
| No SLOs (availability/performance targets) | Unclear reliability goals | P3 | Document SLOs (e.g., 99% job completion < X mins) |

## 5. Data & Storage Gaps
| Gap | Impact | Priority | Remediation |
|-----|--------|----------|-------------|
| SQLite in production (no migrations) | Concurrency & evolution limits | P0 | Migrate to PostgreSQL + Alembic migrations |
| No backup automation | Data loss risk | P1 | Add scheduled backup scripts (cron + cloud/offsite storage) |
| No storage cleanup policy implemented (only doc examples) | Disk usage growth | P1 | Implement scheduled cleanup job (retain recent N days) |
| No transcript versioning | Loss of history on edits | P3 | Introduce versioned transcript storage tables |

## 6. Performance & Scalability Gaps
| Gap | Impact | Priority | Remediation |
|-----|--------|----------|-------------|
| Concurrency static (MAX_CONCURRENT_JOBS) | Under/over-utilization on varied hardware | P2 | Implement adaptive concurrency based on load (CPU % / queue depth) |
| No GPU support path | Poor performance for large models | P2 | Add CUDA device detection + optional torch GPU usage |
| Unprofiled inference times | Blind capacity planning | P2 | Add timing metrics & model benchmark report |
| No horizontal scaling design doc | Hard to scale beyond single host | P3 | Architect multi-instance + shared storage (S3/NFS) strategy |

## 7. Accessibility (A11y) Gaps
| Gap | Impact | Priority | Remediation |
|-----|--------|----------|-------------|
| Missing aria-labels on interactive icons (Settings, Clear, Filters) | Screen reader usability impaired | P1 | Add semantic labels & roles |
| Keyboard navigation not validated (modals, dropdowns) | Non-mouse users blocked | P1 | Ensure tab order, ESC close, arrow navigation in menus |
| Color contrast not audited beyond tag badges | Potential readability issues | P2 | Run contrast audit (Lighthouse / axe) & adjust palette |

## 8. Error Handling & Resilience Gaps
| Gap | Impact | Priority | Remediation |
|-----|--------|----------|-------------|
| No global error boundary in frontend | Catastrophic errors crash UI | P1 | Implement React ErrorBoundary with fallback + report |
| Silent API failures (missing toast on fetch errors) | Poor user feedback | P1 | Wrap fetch calls with centralized error -> toast dispatcher |
| Job restart logic simulated only | Inconsistent recovery path | P2 | Implement idempotent restart endpoint + UI wiring |
| No queue depth safeguards (max inflight jobs beyond concurrency) | Potential overload | P2 | Validate job submission against backlog threshold |

## 9. Developer Experience Gaps
| Gap | Impact | Priority | Remediation |
|-----|--------|----------|-------------|
| No pre-commit hooks (lint/test/type-check) | Inconsistent quality | P1 | Add Husky (frontend) + pre-commit (backend) config |
| No CI pipeline | Manual validation burden | P0 | GitHub Actions workflows for lint, test, build, Docker push |
| No architectural diagram checked into repo | Hard onboarding | P2 | Add sequence diagrams & component dependency map |
| Lack of ADRs (Architecture Decision Records) | Rationale loss over time | P3 | Introduce ADR folder documenting key choices |

## 10. Documentation Gaps
| Gap | Impact | Priority | Remediation |
|-----|--------|----------|-------------|
| API error codes & examples undocumented | Client resilience harder | P2 | Extend API_CONTRACTS with status codes & failure bodies |
| Missing upgrade/migration guide | Risk during schema changes | P2 | Add MIGRATION_GUIDE.md (DB, model updates) |
| Security hardening playbook shallow | Operational risk | P1 | Create SECURITY.md with actionable steps |
| No CONTRIBUTING.md | Fewer external contributions | P3 | Add contribution workflow & coding standards |

## 11. Prioritized Remediation Roadmap (Suggested Sprints)

### Sprint 1 (Stabilization & Core Reliability)
- Implement real API wiring in frontend (P0)
- Migrate to PostgreSQL + Alembic (P0)
- Fix frontend test runner & execute test suite (P0)
- Introduce CI pipeline (P0)
- Add rate limiting + password policy (P0/P1)

### Sprint 2 (Quality & Observability)
- Playwright E2E baseline (P0)
- Structured logging + metrics instrumentation (P1)
- Accessibility pass (labels, keyboard, contrast) (P1/P2)
- Error boundary + centralized fetch error handling (P1)
- Backup + storage cleanup automation (P1)

### Sprint 3 (Performance & Security Hardening)
- Adaptive concurrency logic (P2)
- GPU support detection (P2)
- Benchmark & profiling instrumentation (P2)
- JWT refresh + lockout strategy (P1/P2)
- SECURITY.md + MIGRATION_GUIDE.md (P1/P2)

### Sprint 4 (Enhancement & Extensibility)
- Transcript editing + versioning (P3)
- Batch upload feature (P3)
- Architectural diagrams & ADRs (P2/P3)
- Horizontal scaling design doc (P3)
- CONTRIBUTING.md (P3)

## 12. Success Metrics for Remediation
| Metric | Target |
|--------|--------|
| Frontend unit test pass rate | 100% |
| Backend unit test pass rate | 100% |
| E2E workflow coverage | Upload → Complete → Export (core path) |
| Mean transcription queue wait | < 10s (medium model) |
| Error responses with structured body | 100% of non-2xx |
| Accessibility automated score (Lighthouse) | ≥ 90 |
| Coverage (backend/frontend) | ≥ 80% / 70% maintained |
| Mean time to recovery from failed job | < 1 retry cycle |

## 13. Risk Assessment Summary
- **Highest Risks**: Lack of real data wiring, missing E2E tests, production DB migration path, absent rate limiting.
- **Moderate Risks**: Observability gaps, accessibility issues, unexecuted test suite.
- **Long-Term Risks**: Scaling constraints (SQLite, no horizontal plan), maintainability without ADRs.

## 14. Blockers & Assumptions
- Assumes backend API endpoints behave per contracts (not revalidated here).
- Assumes model files present and accessible—no integrity verification implemented.
- Assumes test hanging issue solvable via dependency/version adjustments.

## 15. Summary
Immediate focus must shift from feature completeness to operational hardening and validation. Addressing P0/P1 gaps establishes a trustworthy baseline for wider adoption and future enhancements. The current codebase is a strong functional foundation; targeted remediation accelerates maturity.

---
Prepared as follow-up to POST_MORTEM.md to guide execution toward production-grade readiness.
