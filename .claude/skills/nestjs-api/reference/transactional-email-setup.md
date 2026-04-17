# Transactional Email Setup Pattern

## Provider Selection

Use a dedicated transactional email provider. Do NOT use Firebase Auth emails for transactional messages (order confirmations, notifications, etc.) — Firebase Auth emails are for auth flows only.

Recommended providers:
- **Resend** — modern API, great DX, generous free tier
- **SendGrid** — mature, high deliverability, good analytics
- **Postmark** — best deliverability, strict anti-spam policy

## DNS Configuration (Required for Deliverability)

### SPF Record

Add to your domain's DNS TXT record:

```
v=spf1 include:_spf.google.com include:<provider-spf> ~all
```

Replace `<provider-spf>` with your provider's SPF domain (e.g., `sendgrid.net`, `amazonses.com`).

### DKIM Record

Each provider generates a DKIM key pair. Add the public key as a DNS TXT record:

```
<selector>._domainkey.yourdomain.com  TXT  "v=DKIM1; k=rsa; p=<public-key>"
```

### DMARC Record

```
_dmarc.yourdomain.com  TXT  "v=DMARC1; p=quarantine; rua=mailto:dmarc@yourdomain.com; pct=100"
```

Start with `p=none` for monitoring, escalate to `p=quarantine` after verifying alignment.

## Implementation Pattern (NestJS)

```typescript
// email.module.ts
@Module({
  providers: [EmailService],
  exports: [EmailService],
})
export class EmailModule {}

// email.service.ts
@Injectable()
export class EmailService {
  private readonly logger = new Logger(EmailService.name);
  private readonly client: Resend; // or SendGrid client

  constructor(private readonly config: ConfigService) {
    this.client = new Resend(this.config.getOrThrow('RESEND_API_KEY'));
  }

  async sendTransactional(to: string, subject: string, html: string): Promise<void> {
    try {
      await this.client.emails.send({
        from: this.config.getOrThrow('EMAIL_FROM'),
        to,
        subject,
        html,
      });
      this.logger.log(`Email sent to ${to}: ${subject}`);
    } catch (error) {
      this.logger.error(`Email send failed to ${to}`, error);
      throw error; // Never swallow — caller decides retry strategy
    }
  }
}
```

## Bounce and Complaint Monitoring

- Configure webhook endpoints for bounces and complaints from your provider
- Hard bounces: immediately mark email as invalid, stop sending
- Complaints: immediately unsubscribe, investigate template/frequency
- Monitor bounce rate — stay below 2% to maintain deliverability

## Checklist

- [ ] SPF record configured and verified
- [ ] DKIM record configured and verified
- [ ] DMARC record configured (start with `p=none`)
- [ ] Bounce webhook endpoint implemented
- [ ] Complaint webhook endpoint implemented
- [ ] Email templates tested with mail-tester.com (score >= 8/10)
