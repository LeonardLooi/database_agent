# Package Evaluation — Flutter 3.41.x / Dart 3.10.9

Use before adding any pub.dev dependency. Applies to: Flutter 3.41.x / Dart 3.10.9 / pub.dev (as of 2026).

---

## Section 1 — pub.dev quality signals

Before adding any pub.dev dependency, evaluate ALL of the following:

| Signal | Threshold | Where to check |
|--------|-----------|----------------|
| Pub points | ≥ 130 / 160 | pub.dev package page score badge |
| Likes | Context-dependent (>100 for utilities, >500 for UI) | pub.dev likes count |
| Popularity | > 70% for general-use packages | pub.dev popularity % |
| Verified publisher | Must have verified publisher badge | pub.dev publisher badge (e.g., dart.dev, google.dev) |
| Null safety | Must support null safety | Dart 3 null safety badge |
| Last publish | < 12 months for active packages (exception: stable packages with no churn) | pub.dev "Published" date |
| Platform support | Must include iOS + Android for mobile packages | Platform tags on pub.dev |
| License | MIT, Apache 2.0, or BSD only | pub.dev license tab |

---

## Section 2 — License compatibility

| License | Mobile app use | Commercial use | Requires attribution |
|---------|---------------|----------------|---------------------|
| MIT | ✅ | ✅ | In app credits or NOTICE file |
| Apache 2.0 | ✅ | ✅ | In NOTICE file |
| BSD 2/3-clause | ✅ | ✅ | In app credits or NOTICE file |
| GPL v2/v3 | ❌ | ❌ | Copyleft — infects your app |
| LGPL | ⚠️ | ⚠️ | Dynamic linking only — get legal review |
| Proprietary | ⚠️ | ⚠️ | Check terms before use |

**Rule:** NEVER add a GPL-licensed package to a closed-source Flutter app without explicit legal
approval. GPL copyleft applies to the entire binary — it is not safe to assume "library use" is
exempt for statically linked mobile apps.

---

## Section 3 — Pre-add checklist

```
Before adding any pub.dev package:
□ Pub points ≥ 130
□ Verified publisher (or explicitly justified in PR)
□ License = MIT / Apache 2.0 / BSD
□ Null safety supported
□ Last published within 12 months (or stable/no-churn exception documented)
□ Package solves a problem we cannot solve reasonably ourselves
□ Not a thin wrapper around standard library (implement directly instead)
□ Open issues checked for critical/blocking bugs in our use case
```

---

## Section 4 — Red flags

- Package with 0 verified publisher AND < 50 pub points — likely unmaintained or low quality
- Package that hasn't been published in > 2 years — check if officially deprecated
- Package that requires platform-specific permissions beyond what it actually needs
- Multiple packages doing the same thing in `pubspec.yaml` — pick one and standardize
- Forked packages (`*_fork`, `*_fixed`) without explanation — prefer waiting for upstream fix
- Package with < 10 pub points — almost certainly not production-ready

---

## Section 5 — Recommended evaluation workflow

```bash
# 1. Visit pub.dev/packages/<package_name>
#    Check: score, verified publisher, license, last publish date, platform tags

# 2. Read CHANGELOG for breaking changes in latest version

# 3. Check Issues tab for critical bugs affecting your use case

# 4. Add the package:
flutter pub add <package_name>

# 5. Audit for known vulnerabilities:
flutter pub audit
# Exit code 0 = no known vulnerabilities. Any HIGH/CRITICAL = block the add.
```

**`flutter pub audit`** is the equivalent of `npm audit` — it checks all transitive dependencies
against the OSV vulnerability database. Run it after every `pub add` or `pub upgrade`.

---

## Section 6 — Version pinning

Pin to an exact version in `pubspec.yaml` for stability. Never use `any` or loose ranges in
production:

```yaml
dependencies:
  # Correct — pinned to exact version
  go_router: 14.6.3

  # Acceptable — minor version range (API stable within minor)
  riverpod: ^3.2.1

  # Forbidden in production
  some_package: any
  other_package: ">=1.0.0"  # unbounded upper bound
```

When upgrading, run `flutter pub outdated` to see what has updates, then evaluate each upgrade
with the pre-add checklist (Section 3) before accepting.
