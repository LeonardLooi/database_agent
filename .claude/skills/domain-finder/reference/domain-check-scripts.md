# Domain Availability Check Scripts

Shell scripts and commands for checking domain name availability using DNS and WHOIS lookups.

## DNS Batch Check

Quick batch check using `dig`. An `NXDOMAIN` or `SERVFAIL` response strongly suggests the domain is unregistered:

```bash
# Quick batch check — NXDOMAIN = likely available
for domain in snippetbox.com codeclip.io devpaste.dev; do
  result=$(dig +short "$domain" 2>/dev/null)
  if [ -z "$result" ]; then
    status=$(dig "$domain" +noall +comments 2>/dev/null | grep -o 'NXDOMAIN\|NOERROR\|SERVFAIL')
    if [ "$status" = "NXDOMAIN" ]; then
      echo "✅ $domain — likely available"
    else
      echo "⚠️  $domain — parked or no A record (check registrar)"
    fi
  else
    echo "❌ $domain — taken ($result)"
  fi
done
```

## WHOIS Deep Check

For deeper verification when DNS results are inconclusive:

```bash
# WHOIS check for a specific domain
whois snippetbox.com 2>/dev/null | grep -iE "^(Domain Name|Registry|Creation|Expir|No match|NOT FOUND|No Data)"
```

**Interpreting results:**
- `No match` / `NOT FOUND` / `No Data Provided` → available
- `Creation Date` present → registered
- No WHOIS response → try the DNS method above

## Social Handle Check

Verify social media availability for the chosen domain name:

```bash
# Check if GitHub username/org is taken (404 = available)
for name in snippetdev codeclip snipflow; do
  status=$(curl -s -o /dev/null -w "%{http_code}" "https://github.com/$name")
  if [ "$status" = "404" ]; then
    echo "✅ github.com/$name — available"
  else
    echo "❌ github.com/$name — taken"
  fi
done
```

## TLD Quick Reference

| TLD | Best For | Price Range |
|-----|----------|-------------|
| `.com` | Universal, trusted, any business | ~$10–15/yr |
| `.io` | Tech startups, developer tools | ~$30–50/yr |
| `.dev` | Developer-focused products | ~$12–15/yr |
| `.ai` | AI/ML products | ~$30–80/yr |
| `.app` | Mobile or web applications | ~$12–15/yr |
| `.co` | Startups, .com alternative | ~$25–35/yr |
| `.xyz` | Creative/experimental projects | ~$10–12/yr |

## Output Format Template

```
🎯 Domain Name Results for [Project Description]

AVAILABLE
  ✅ snippet.dev         — short, .dev signals developer tool
  ✅ codeclip.com        — 8 chars, memorable compound word
  ✅ snipflow.io         — brandable, implies movement

LIKELY AVAILABLE (verify at registrar)
  ⚠️  devpaste.app       — no DNS record, WHOIS inconclusive

TAKEN
  ❌ codeshare.com       — registered, has active site
  ❌ snippets.com        — premium domain

🏆 TOP PICK: snippet.dev
   Short, memorable, perfect TLD for developer audience

🥈 RUNNER-UP: codeclip.com
   .com credibility, only 8 characters, highly brandable

NEXT STEPS
  1. Register your pick before it's gone
  2. Grab the .com + one alt TLD to protect the brand
  3. Check @handle availability on GitHub/Twitter/LinkedIn
```

## Tips to Share with User
- **Act fast** — good domains disappear quickly
- **Register 2 TLDs** — primary + .com to protect brand
- **Say it out loud** — if it's awkward to say, pick another
- **Search trademarks** — check USPTO/EUIPO before committing
- **Think 5 years out** — avoid trend-dependent names
