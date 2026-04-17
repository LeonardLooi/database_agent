# Cloud Run Functions — Event-Driven Patterns

## Overview

Cloud Run Functions are containerized handlers invoked by:
- **Pub/Sub push** — GCP pushes a base64-encoded message to your HTTP endpoint
- **Cloud Storage notification** — Eventarc routes object events to your endpoint
- **HTTP webhook** — Direct HTTP invocation (authenticated via IAM or API Gateway)

All patterns share the same container model: build a Docker image, deploy to Cloud Run.

---

## Python FastAPI (python:3.14-slim)

### Pub/Sub Push Handler

```python
# main.py
import base64
import json
import logging
import os
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
app = FastAPI()

class PubSubMessage(BaseModel):
    data: str      # base64-encoded payload
    messageId: str
    publishTime: str

class PubSubEnvelope(BaseModel):
    message: PubSubMessage
    subscription: str

@app.post("/")
async def handle_pubsub(envelope: PubSubEnvelope) -> dict:
    try:
        payload = json.loads(base64.b64decode(envelope.message.data).decode("utf-8"))
        logger.info("Received message", extra={"messageId": envelope.message.messageId, "payload": payload})
        # TODO: process payload
        return {"status": "ok"}
    except Exception as e:
        logger.error("Failed to process Pub/Sub message", exc_info=e)
        # Return 500 so Cloud Run retries (do NOT return 200 on failure)
        raise HTTPException(status_code=500, detail="Processing failed")

@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), workers=1)
```

### Cloud Storage Trigger Handler

```python
@app.post("/storage")
async def handle_storage(request: Request) -> dict:
    event = await request.json()
    bucket = event.get("bucket")
    name = event.get("name")
    event_type = event.get("eventType")
    logger.info("Storage event", extra={"bucket": bucket, "name": name, "eventType": event_type})
    # TODO: process file event
    return {"status": "ok"}
```

### Dockerfile Reference

Use `python:3.14-slim` base — see `docker` skill `reference/dockerfiles.md` for the full Python multi-stage template.
Port binding: `CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]`

---

## NestJS / Fastify (node:24-alpine)

### Pub/Sub Push Handler

```typescript
// src/pubsub/pubsub.controller.ts
import { Controller, Post, Get, Body, HttpException, HttpStatus, Logger } from '@nestjs/common';

interface PubSubMessage {
  data: string;        // base64-encoded
  messageId: string;
  publishTime: string;
}

interface PubSubEnvelope {
  message: PubSubMessage;
  subscription: string;
}

@Controller()
export class PubSubController {
  private readonly logger = new Logger(PubSubController.name);

  @Post()
  async handlePubSub(@Body() envelope: PubSubEnvelope): Promise<{ status: string }> {
    try {
      const payload = JSON.parse(Buffer.from(envelope.message.data, 'base64').toString('utf-8'));
      this.logger.log({ messageId: envelope.message.messageId, payload });
      // TODO: delegate to service
      return { status: 'ok' };
    } catch (error) {
      this.logger.error('Failed to process Pub/Sub message', error);
      throw new HttpException('Processing failed', HttpStatus.INTERNAL_SERVER_ERROR);
    }
  }

  @Get('/health')
  health(): { status: string } {
    return { status: 'ok' };
  }
}
```

### Bootstrap for Cloud Run

```typescript
// src/main.ts
import { NestFactory } from '@nestjs/core';
import { FastifyAdapter, NestFastifyApplication } from '@nestjs/platform-fastify';
import { AppModule } from './app.module';

async function bootstrap() {
  const app = await NestFactory.create<NestFastifyApplication>(AppModule, new FastifyAdapter());
  const port = parseInt(process.env.PORT ?? '8080', 10);
  await app.listen(port, '0.0.0.0');
}
bootstrap();
```

### Dockerfile Reference

Use `node:24-alpine` base — see `docker` skill `reference/dockerfiles.md` for the full NestJS multi-stage template.

---

## Spring Boot WebFlux (eclipse-temurin:21-jre-alpine)

### Pub/Sub Push Handler

```java
// PubSubController.java
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import reactor.core.publisher.Mono;
import java.util.Base64;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

@RestController
public class PubSubController {

    private static final Logger log = LoggerFactory.getLogger(PubSubController.class);
    private final ObjectMapper objectMapper;

    public PubSubController(ObjectMapper objectMapper) {
        this.objectMapper = objectMapper;
    }

    record PubSubMessage(String data, String messageId, String publishTime) {}
    record PubSubEnvelope(PubSubMessage message, String subscription) {}

    @PostMapping("/")
    public Mono<ResponseEntity<Void>> handlePubSub(@RequestBody PubSubEnvelope envelope) {
        return Mono.fromCallable(() -> {
            byte[] decoded = Base64.getDecoder().decode(envelope.message().data());
            var payload = objectMapper.readTree(decoded);
            log.info("Received message messageId={} payload={}", envelope.message().messageId(), payload);
            // TODO: delegate to service
            return ResponseEntity.<Void>ok().build();
        })
        .onErrorResume(e -> {
            log.error("Failed to process Pub/Sub message messageId={}", envelope.message().messageId(), e);
            // Return 500 so Pub/Sub retries
            return Mono.just(ResponseEntity.<Void>internalServerError().build());
        });
    }

    @GetMapping("/health")
    public Mono<ResponseEntity<String>> health() {
        return Mono.just(ResponseEntity.ok("{\"status\":\"ok\"}"));
    }
}
```

> **Rule:** Never block in a WebFlux pipeline. Use `Mono.fromCallable` for CPU-bound work, delegate I/O to reactive clients.

### Dockerfile Reference

Use `eclipse-temurin:21-jre-alpine` runtime stage — see `docker` skill `reference/dockerfiles.md` for the full Java multi-stage template.

---

## TypeScript / Fastify (node:24-alpine)

### Pub/Sub Push Handler

```typescript
// src/index.ts
import Fastify from 'fastify';
import { z } from 'zod';

const PubSubMessageSchema = z.object({
  data: z.string(),           // base64-encoded
  messageId: z.string(),
  publishTime: z.string(),
});

const PubSubEnvelopeSchema = z.object({
  message: PubSubMessageSchema,
  subscription: z.string(),
});

const app = Fastify({ logger: true });

app.post('/', async (request, reply) => {
  const result = PubSubEnvelopeSchema.safeParse(request.body);
  if (!result.success) {
    request.log.error({ errors: result.error.issues }, 'Invalid Pub/Sub envelope');
    return reply.code(400).send({ error: 'Invalid envelope' });
  }
  try {
    const payload = JSON.parse(Buffer.from(result.data.message.data, 'base64').toString('utf-8'));
    request.log.info({ messageId: result.data.message.messageId, payload });
    // TODO: process payload
    return reply.code(200).send({ status: 'ok' });
  } catch (err) {
    request.log.error(err, 'Failed to process Pub/Sub message');
    return reply.code(500).send({ error: 'Processing failed' });
  }
});

app.get('/health', async (_request, reply) => {
  return reply.code(200).send({ status: 'ok' });
});

const port = parseInt(process.env.PORT ?? '8080', 10);
app.listen({ port, host: '0.0.0.0' }).catch((err) => {
  app.log.error(err);
  process.exit(1);
});
```

### Dockerfile Reference

Use `node:24-alpine` base — see `docker` skill `reference/dockerfiles.md` for the Node/TypeScript multi-stage template.

---

## Pub/Sub Return Code Contract

| Scenario | HTTP Status | Effect |
|----------|------------|--------|
| Success | 200–299 | Message acknowledged, not retried |
| Transient error | 500 | Message retried by Pub/Sub (up to retry policy limit) |
| Poison pill / bad payload | 200 | Acknowledge to prevent infinite retry loop |
| Invalid schema | 400 | GCP does NOT retry 4xx — message is dropped |

> Return 500 for processing errors you want retried. Return 200 for messages you explicitly want to discard.

---

## gcloud CLI Alternative (Quick Prototyping)

```bash
# Deploy from source (builds and pushes automatically — dev/prototyping only)
gcloud run deploy my-function \
  --source . \
  --region us-central1 \
  --platform managed \
  --no-allow-unauthenticated \
  --set-env-vars PROJECT_ID=$PROJECT_ID

# Set up Pub/Sub push subscription to the deployed function
FUNCTION_URL=$(gcloud run services describe my-function --region us-central1 --format 'value(status.url)')
gcloud pubsub subscriptions create my-sub \
  --topic my-topic \
  --push-endpoint "$FUNCTION_URL/" \
  --push-auth-service-account my-sa@$PROJECT_ID.iam.gserviceaccount.com
```

> For production, use the GitHub Actions workflow in `SKILL.md` — not `gcloud run deploy --source`.
