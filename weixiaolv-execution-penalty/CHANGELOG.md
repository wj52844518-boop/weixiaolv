# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [1.0.0] - 2026-06-15

### Added

- **Initial release**: Independent GitHub repository for weixiaolv-execution-penalty
- **Three-engine architecture**: trigger_checker + route_selector + evidence_mapper
- **法释〔2024〕13号** full implementation:
  - 10 "情节严重" trigger codes (T1–T8)
  - 3 "情节特别严重" codes (TS1–TS3)
  - T1.5 pre-judgment transfer detection (new in 2024)
  - De facto controller subject expansion (§2)
- **法发〔2025〕8号** full implementation:
  - 30-day self-prosecution window auto-calculation
  - Three-path prosecution route decision tree
  - "Beyond reasonable doubt" evidence chain mapper
- **Claude Desktop plugin metadata**: plugin.json + marketplace.json
- **Bilingual README**: Chinese + English
- **CONNECTORS.md**: Neo4j / Feishu optional integration spec
- **penalty_report_schema.json**: JSON Schema for tactical payload
- **GitHub Actions CI**: flake8 linting + pyright type check + structure validation
