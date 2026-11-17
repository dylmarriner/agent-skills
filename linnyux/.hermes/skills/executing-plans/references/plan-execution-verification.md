# Plan execution verification notes

Session-derived checklist for executing implementation plans:

- Track the plan as a todo list and keep exactly one item in progress at a time.
- Run the narrowest relevant verification after each major package change:
  - backend: type-check first, then targeted tests if the plan touched behavior
  - frontend: type-check first, then production build when UI routing/data hooks changed
- Treat build-time warnings separately from failures.
  - Example: Next.js sitemap fetch warnings caused by a local backend being offline can be non-blocking if the build exits 0.
  - Only stop when the build/test command returns a failing exit code or the app behavior is genuinely broken.
- If a patch introduces LSP diagnostics or type errors, rerun the package type-check immediately rather than assuming the edit is fine.
- Before closing the task, confirm the exact verification commands and their exit codes in the final report.
