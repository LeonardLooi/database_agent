# SDK Generation and CI/CD Integration

Commands and workflows for generating client SDKs from OpenAPI specs and integrating validation into CI/CD pipelines.

## SDK Generation

### Installation

```bash
npm install -g @openapitools/openapi-generator-cli
```

### TypeScript Client

```bash
openapi-generator-cli generate \
  -i openapi.yaml \
  -g typescript-fetch \
  -o ./generated/ts-client \
  --additional-properties=supportsES6=true,npmName=@myorg/api-client
```

### Python Client

```bash
openapi-generator-cli generate \
  -i openapi.yaml \
  -g python \
  -o ./generated/python-client \
  --additional-properties=packageName=api_client
```

### Java Client

```bash
openapi-generator-cli generate \
  -i openapi.yaml \
  -g java \
  -o ./generated/java-client \
  --additional-properties=library=webclient,dateLibrary=java8
```

### Common Generator Options

| Generator | Key Properties | Notes |
|-----------|---------------|-------|
| `typescript-fetch` | `supportsES6`, `npmName`, `npmVersion` | Browser + Node.js compatible |
| `typescript-axios` | `npmName`, `withSeparateModelsAndApi` | Axios-based, good for Node.js |
| `python` | `packageName`, `projectName` | Uses urllib3 by default |
| `python-pydantic-v1` | `packageName` | Pydantic model generation |
| `java` | `library`, `dateLibrary`, `groupId` | Libraries: webclient, resttemplate, okhttp-gson |
| `dart-dio` | `pubName`, `pubAuthor` | For Flutter/Dart projects |
| `kotlin` | `library`, `groupId` | Libraries: jvm-okhttp4, jvm-retrofit2 |

### Best Practices for SDK Generation

- Pin the generator version in CI to avoid breaking changes
- Set `operationId` on every endpoint -- generators use it for method names
- Use `$ref` for shared schemas -- produces cleaner generated code
- Include examples in the spec -- some generators use them for documentation
- Run `openapi-generator-cli validate` before generating to catch issues early

---

## CI/CD Integration

### GitHub Actions Workflow

```yaml
# .github/workflows/api-docs.yml
name: API Docs
on: [push, pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Lint OpenAPI spec
        uses: stoplightio/spectral-action@v0.8.10
        with:
          file_glob: "openapi.yaml"

      - name: Build docs
        run: npx @redocly/cli build-docs openapi.yaml -o docs/index.html

      - name: Upload docs
        uses: actions/upload-artifact@v4
        with:
          name: api-docs
          path: docs/
```

### Extended Pipeline (Validate + Generate + Publish)

```yaml
# .github/workflows/api-full.yml
name: API Full Pipeline
on:
  push:
    paths:
      - "openapi.yaml"
      - ".spectral.yaml"

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Lint OpenAPI spec
        uses: stoplightio/spectral-action@v0.8.10
        with:
          file_glob: "openapi.yaml"

  generate-sdk:
    needs: validate
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Generate TypeScript client
        run: |
          npx @openapitools/openapi-generator-cli generate \
            -i openapi.yaml \
            -g typescript-fetch \
            -o ./generated/ts-client \
            --additional-properties=supportsES6=true,npmName=@myorg/api-client

      - name: Upload generated client
        uses: actions/upload-artifact@v4
        with:
          name: ts-client
          path: generated/ts-client/

  publish-docs:
    needs: validate
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build docs
        run: npx @redocly/cli build-docs openapi.yaml -o docs/index.html

      - name: Deploy to GitHub Pages
        uses: peaceiris/actions-gh-pages@v3
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./docs
```

### Pipeline Checklist

- Lint the spec on every PR (Spectral or Redocly)
- Build docs artifact for review
- Generate SDKs after spec validation passes
- Run contract tests against generated clients
- Publish docs on merge to main
- Version the spec file with semantic versioning
