# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
versioning follows [SemVer](https://semver.org/).

## [Unreleased]

## [0.1.0] - 2026-08-26

### Added
- Core `RRCNASDecoder`: RRC (BCCH/PCCH/CCCH/DCCH) and NAS hex decoding via pycrate
- NAS decoding now uses `to_json()` for fully structured, named-field output
  (previously fell back to a text dump for message types without a working
  `to_dict()`)
- FastAPI + Pydantic API (`/decode`, `/health`)
- Streamlit GUI, supports both in-process and API-backed decode modes
- pytest suite covering decoder and API layers
- GitHub Actions CI (lint + test matrix across Python 3.10-3.12 + Docker build check)
- Dockerfile for Hugging Face Spaces (Streamlit GUI) and standalone API image
