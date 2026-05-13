# Detection Report Format

This file is merged into report-template.md — see references/report-template.md for the full format.
The detection report is output at the end of Phase 0.

Key fields per detected component:
- name, type, config file path, exposed port
- risk level: LOW / MEDIUM / HIGH (see scoring criteria in report-template.md)
- existing test files found and estimated coverage percentage

After the component table, output:
- Auto-added services (anything detected but not in the default stack)
- Coverage gap summary table (layers × files found vs files with tests)
