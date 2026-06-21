---
name: no-identity-en-us-po-entries
description: Don't add identity (msgstr == msgid) entries to the en_US .po catalog
metadata:
  type: feedback
---

When adding new translatable UI strings, add the entry only to `ru_RU` (`sportorg/data/languages/ru_RU/LC_MESSAGES/sportorg.po`). Do NOT add a matching identity entry to the `en_US` catalog.

**Why:** gettext falls back to the `msgid` itself when a string is absent from the catalog, so English already renders correctly without an explicit `msgstr == msgid` entry. The user considers those identity entries redundant noise.

**How to apply:** For each new `translate("...")` string, append a `msgid`/`msgstr` pair to the ru_RU `.po` only, then run `uv run poe generate-mo`. Skip en_US.
