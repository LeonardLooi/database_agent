# Google Play Submission Preflight Checklist

Complete all 5 steps before releasing to production track.

## Step 1: Validate Edit (if using edit lifecycle)

Edit must validate without errors before commit.

```bash
gpd publish edit validate EDIT_ID --package com.example.app
```

Expected: no validation errors in output. If errors exist — fix before proceeding.

## Step 2: Confirm Release Status

Release status and version code must match the intended build.

```bash
gpd publish status --package com.example.app --track production
```

Check:
- Release status is expected (`draft`, `inProgress`, or `completed`)
- Version code matches the uploaded build
- No unexpected releases on the track

## Step 3: Verify Store Listing Metadata

All required metadata fields must be present for all active locales.

```bash
gpd publish listing get --package com.example.app
gpd publish details get --package com.example.app
```

Required fields per locale:
- Title (≤ 30 characters)
- Short description (≤ 80 characters)
- Full description (≤ 4000 characters)
- Contact email

## Step 4: Verify Screenshots and Assets

All required screenshot types must be uploaded for each active locale.

```bash
gpd publish images list phoneScreenshots --package com.example.app --locale en-US
gpd publish assets spec
```

Required asset types:
- Phone screenshots (minimum 2, maximum 8)
- Feature graphic (1024 × 500 px)
- App icon (512 × 512 px)

Upload missing assets:
```bash
gpd publish images upload icon icon.png --package com.example.app --locale en-US
gpd publish assets upload ./assets --package com.example.app
```

## Step 5: Upload Deobfuscation Mapping (if applicable)

Required if your build uses ProGuard or R8 obfuscation.

```bash
gpd publish deobfuscation upload mapping.txt \
  --package com.example.app \
  --type proguard \
  --version-code 123
```

Only needed if obfuscation is enabled. Skip if your build does not use ProGuard/R8.
