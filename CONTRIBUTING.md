# Contributing

Thanks for considering a contribution — patches, bug reports, docs, and new
protocol coverage are all welcome.

## Getting set up

```bash
git clone https://github.com/<your-username>/4glte-decoder.git
cd 4glte-decoder
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pytest tests/ -v
```

If `pytest` passes, you're ready to go.

## Before opening a PR

1. **Add or update tests.** Every decoder behavior change needs a test in
   `tests/test_decoder.py` or `tests/test_api.py`. PRs that only add
   features without tests will be asked to add them.
2. **Run the full check locally:**
   ```bash
   ruff check app tests
   pytest tests/ -v --cov=app
   ```
3. **Keep PRs focused.** One feature or fix per PR is much easier to review
   than a bundle of unrelated changes.
4. **Update the README** if you're adding a user-facing feature (new
   endpoint, new channel mapping, new GUI capability).

## What's most useful right now

Check the [issue tracker](../../issues) for `good first issue` and `help
wanted` labels. Broadly, the highest-value contributions are:

- New RRC/NAS message type coverage (anything pycrate supports that isn't
  yet mapped in `RRCNASDecoder`)
- 5G NR support (`pycrate_asn1dir.NRRRC`, `pycrate_mobile.NAS5G`)
- Real-world test vectors (hex captures + expected decode, ideally anonymized
  from public sources — see "Test vectors" below)
- Bug reports with a reproducible hex string

## Test vectors

If you're contributing a new test case, please:
- Confirm the hex is either synthetic/lab-generated or from a public,
  already-published source (e.g. a 3GPP conformance test vector, a public
  Wireshark sample capture).
- **Do not submit hex captured from live commercial networks** without
  confirming it contains no real subscriber identifiers (IMSI, GUTI tied to
  a real device, etc.). When in doubt, use a synthetic example instead.

## Code style

- Formatting/linting is `ruff` (config in `pyproject.toml`) — run
  `ruff check app tests` before pushing.
- Type hints are encouraged on new functions, not required on existing code
  you're not touching.
- Keep `RRCNASDecoder` framework-agnostic — it shouldn't import from
  `app.api` or `app.streamlit_app`. The API and GUI depend on the decoder,
  never the other way around.

## Reporting bugs

Please include:
- The hex string that fails (see the test vector note above)
- `layer` / `channel` / `direction` you used
- Full error output
- pycrate version (`pip show pycrate`)

## Code of Conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md). Be kind.
