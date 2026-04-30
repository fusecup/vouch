<!--
Sync Impact Report:
Version change: [NEW] → 1.0.0
Modified principles: N/A (new constitution)
Added sections: Core Principles (4 principles), Quality Gates, Governance
Removed sections: N/A
Templates requiring updates:
  ✅ plan-template.md - Updated Constitution Check section reference
  ✅ spec-template.md - No changes needed (already references testing)
  ✅ tasks-template.md - No changes needed (already references testing)
  ⚠️ Manual review recommended for command files in .cursor/commands/
Follow-up TODOs: None
-->

# FuseCup Constitution

## Core Principles

### I. Code Quality (NON-NEGOTIABLE)

All code MUST adhere to strict quality standards that ensure maintainability, readability, and correctness. This principle mandates:

- **Linting and Formatting**: All code MUST pass Ruff linting checks with zero errors before merge. Code formatting MUST follow PEP 8 standards and project-specific style guidelines.
- **Code Review**: All changes MUST undergo peer code review. Reviews MUST verify adherence to architectural patterns, error handling, security best practices, and this constitution.
- **Documentation**: Public APIs, complex business logic, and architectural decisions MUST be documented. Inline comments MUST explain "why" not "what" for non-obvious code.
- **Refactoring Discipline**: Technical debt MUST be addressed incrementally. Code smell accumulation beyond acceptable thresholds triggers mandatory refactoring sprints.
- **Dependency Management**: Dependencies MUST be justified and kept minimal. Security vulnerabilities MUST be patched within 48 hours of identification. Use `uv` for Python package management exclusively.

**Rationale**: High code quality reduces bug introduction, accelerates onboarding, and ensures long-term maintainability. Quality gates prevent technical debt accumulation that degrades velocity over time.

### II. Testing Standards (NON-NEGOTIABLE)

Comprehensive testing is mandatory at multiple levels to ensure reliability and prevent regressions. This principle requires:

- **Test Coverage**: All new features MUST include tests. Coverage thresholds: minimum 80% for new code, critical paths require 95%+. Coverage reports MUST be generated and reviewed.
- **Test Types**: Unit tests for isolated logic, integration tests for component interactions, and end-to-end tests for critical user journeys. Contract tests REQUIRED for API boundaries.
- **Test-First When Applicable**: Complex business logic SHOULD follow TDD (Test-Driven Development) where tests are written before implementation. This applies especially to algorithms, validators, and state machines.
- **Test Quality**: Tests MUST be independent, deterministic, and fast. Flaky tests are treated as blocking issues. Tests MUST clearly express intent through descriptive names and assertions.
- **Continuous Integration**: All tests MUST pass in CI before merge. Test failures block deployments. Performance regression tests MUST be included for critical paths.

**Rationale**: Robust testing prevents production failures, enables confident refactoring, and serves as living documentation. Testing discipline is the foundation of reliable software delivery.

### III. User Experience Consistency

User-facing features MUST provide consistent, intuitive, and accessible experiences across all interaction points. This principle mandates:

- **Design System Compliance**: UI components MUST use the established design system (TailwindCSS + Django-cotton). Custom styling MUST be justified and documented. Never edit `tw-styles.css` directly—use Tailwind utility classes only.
- **Accessibility Standards**: All interfaces MUST meet WCAG 2.1 Level AA minimum. Keyboard navigation, screen reader support, and semantic HTML are REQUIRED.
- **Error Handling**: User-facing errors MUST be clear, actionable, and consistent in tone. Error messages MUST avoid technical jargon and provide next steps.
- **Responsive Design**: All interfaces MUST function correctly across desktop, tablet, and mobile viewports. Mobile-first approach preferred.
- **Performance Perception**: Perceived performance matters. Loading states, skeleton screens, and progressive enhancement (HTMX + Alpine.js) MUST be used to provide immediate feedback.
- **Consistency Across Features**: Similar functionality MUST behave similarly across the application. Navigation patterns, form behaviors, and interaction models MUST be consistent.

**Rationale**: Consistent UX reduces cognitive load, improves user satisfaction, and decreases support burden. Users form mental models based on consistency, which accelerates task completion.

### IV. Performance Requirements

System performance MUST meet defined thresholds to ensure acceptable user experience and operational efficiency. This principle requires:

- **Response Time Targets**: API endpoints MUST respond within defined SLA thresholds (e.g., p95 < 200ms for standard operations, p99 < 500ms for complex queries). Database queries MUST be optimized using `select_related`/`prefetch_related` and proper indexing.
- **Database Optimization**: N+1 query problems are PROHIBITED. Query performance MUST be monitored and optimized. Database indexes MUST be added for frequently queried fields.
- **Caching Strategy**: Appropriate caching layers (Redis) MUST be used for frequently accessed data. Cache invalidation strategies MUST be implemented correctly.
- **Background Task Processing**: Long-running operations (>2 seconds) MUST be moved to Celery background tasks. User-facing requests MUST remain responsive.
- **Resource Efficiency**: Memory and CPU usage MUST be monitored. Resource leaks are treated as critical bugs. Container resource limits MUST be respected.
- **Scalability Considerations**: Features MUST be designed to handle expected load. Horizontal scaling MUST be possible without architectural changes for stateless components.

**Rationale**: Performance directly impacts user satisfaction and operational costs. Poor performance degrades UX and can cause system failures under load. Proactive performance management prevents reactive firefighting.

## Quality Gates

All code changes MUST pass the following gates before merge:

1. **Linting**: Ruff checks pass with zero errors
2. **Tests**: All tests pass (unit, integration, end-to-end as applicable)
3. **Coverage**: New code meets coverage thresholds (80% minimum, 95% for critical paths)
4. **Performance**: No performance regressions in critical paths (monitored via CI)
5. **Security**: No known security vulnerabilities in dependencies
6. **Documentation**: Public APIs and complex logic documented
7. **Accessibility**: WCAG 2.1 Level AA compliance verified
8. **Constitution Compliance**: All changes align with core principles

## Development Workflow

- **Code Review Process**: At least one approval required. Reviewers MUST verify constitution compliance.
- **Testing Workflow**: Tests MUST be written for new features. Test failures block deployment.
- **Performance Monitoring**: Performance metrics MUST be tracked in production. Regressions trigger immediate investigation.
- **Documentation**: Architecture decisions MUST be documented. API changes require documentation updates.

## Governance

This constitution supersedes all other development practices and guidelines. It represents the foundational principles that govern all technical decisions in the FuseCup project.

**Amendment Process**:

- Amendments require explicit documentation of rationale and impact assessment
- Version changes follow semantic versioning (MAJOR.MINOR.PATCH)
- All team members must acknowledge constitution updates
- Constitution violations in code reviews MUST be addressed before merge

**Compliance Verification**:

- All PRs/reviews MUST verify compliance with applicable principles
- Constitution violations are blocking issues
- Complexity must be justified if it conflicts with simplicity principles
- Use [AGENTS.md](AGENTS.md) for runtime development guidance and Docker-specific workflows

**Enforcement**:

- Automated checks (linting, tests, coverage) enforce technical requirements
- Manual review verifies principle adherence
- Non-compliance blocks merge until resolved

**Version**: 1.0.0 | **Ratified**: 2025-01-27 | **Last Amended**: 2025-01-27
