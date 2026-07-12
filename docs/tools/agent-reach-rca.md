# Agent-Reach RCA Boundary

Agent-Reach can help a developer or administrator investigate blocked
institutions. It must not become part of EIDP's production PDF acquisition
chain.

## Allowed Use

- One-off research for an institution stuck in `site_entry_missing`,
  `target_document_missing`, or `target_document_year_unverified`.
- Reading official pages or GitHub/tool documentation during developer work.
- Generating an RCA note or candidate URL for later EIDP verification.

## Disallowed Use

- Production dependency in the Linux/Web service.
- Direct writes to `school_site`, `document`, `department_yearly`,
  `support_recipient`, or `school_fiscal_year_status`.
- Operator UI feature.
- Automatic acceptance of search results, social media results, or agent output.
- Cookie-based or account-based social channels for production data collection.

## Required Evidence Handling

Agent-Reach output is external research evidence:

```json
{
  "source_channel": "agent_reach",
  "source_type": "developer_research",
  "trust_tier": "t4_search_candidate",
  "auto_accept_allowed": false,
  "requires_official_domain_confirmation": true
}
```

The candidate may enter a review queue only. EIDP must then refetch, classify,
and verify it through the official-domain pipeline before it can become a
`SiteEntry` or `TargetDocument`.

## RCA Flow

1. EIDP marks an institution blocked.
2. An administrator exports or opens an RCA case.
3. Agent-Reach may be used outside the production app to collect candidate
   links and notes.
4. Candidates are returned to EIDP as low-trust review evidence.
5. EIDP validates the official domain, document kind, target fiscal year, and
   institution identity.
6. Only accepted evidence enters production tables.
