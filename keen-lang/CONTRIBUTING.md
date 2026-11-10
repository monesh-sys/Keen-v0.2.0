# Contributing to KEEN

1. Run the tests before and after every change: `python -m unittest discover -s tests -t .`
2. Every new feature needs tests *and* an example in `examples/`.
3. Record language design decisions in `docs/DESIGN_DECISIONS.md` and update `docs/LANGUAGE_SPEC.md`.
4. Keep the core language (`keen/compiler`, `keen/runtime`) independent of frameworks.
5. Do not document or advertise features that are not implemented and tested.
6. Update `CHANGELOG.md`.
