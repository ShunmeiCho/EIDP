# ICT Reverse-Proxy Requirements — EIDP Linux/Web v1

Status: **APP IDENTITY SUPPORT AVAILABLE — ICT CONFIGURATION AND ACCEPTANCE EVIDENCE PENDING**

Audience: the ICT/server administrator who owns the institutional ingress.
EIDP remains `NOT_READY` until the proxy and business-PC path have fresh
acceptance evidence.

## Responsibility Boundary

- **EIDP owns:** the application under `/home/junming/EIDP`, a Streamlit process
  bound to `127.0.0.1:8502`, its loopback health endpoint and application-side
  validation.
- **ICT owns outside the project root:** reverse proxy, TLS, institutional
  authentication, network allowlist, monitoring and off-host backup pull.
- The EIDP team does not edit `/etc`, install host-wide packages or expose
  Streamlit on `0.0.0.0`.

Loopback prevents remote network clients from reaching Streamlit directly. It
does not exclude other local Venus accounts, so loopback alone is not proof of
proxy identity.

## Required Decisions Before Configuration

ICT must provide and the deployment manifest must record:

1. the exact internal HTTPS URL;
2. whether it is a dedicated hostname at `/` (preferred) or `/eidp/`;
3. allowed business-network ranges;
4. the institutional authentication method;
5. whether authentication exposes a stable per-user identifier;
6. the monitoring source allowed to call the health endpoint;
7. the ICT off-host backup destination and receipt mechanism.

## Proxy Requirements

### 1. WebSocket support is mandatory

Streamlit keeps a long-lived WebSocket at `/_stcore/stream` (or
`/eidp/_stcore/stream`). The proxy must use HTTP/1.1 and forward the
`Upgrade`/`Connection` hop-by-hop headers. An HTTP-only proxy is a release
blocker.

Set a long read timeout and disable response buffering for the application
location. The acceptance test must keep an interactive session alive beyond the
proxy's default idle timeout.

### 2. Root and sub-path behavior

A dedicated internal hostname serving `/` is preferred because it avoids prefix
rewrites. If ICT requires a sub-path:

- `/eidp` must redirect to `/eidp/`;
- Streamlit must start with `server.baseUrlPath=eidp`;
- the proxy must preserve the `/eidp/` prefix rather than strip/rewrite it;
- health, static and `_stcore` paths must all resolve below the same prefix.

The chosen path is immutable for a deployment and is recorded in
`run/deployment-manifest.json`.

Application support for the base path, public browser address and explicit CORS origins is **AVAILABLE**;
the runtime controller passes the validated settings to `run_web.sh`. ICT must
still configure and prove the chosen public URL, prefix, WebSocket path and
origin behavior, so that external acceptance evidence remains **PENDING and
release blocking**.

### 3. XSRF, CORS and public origin

Keep `server.enableXsrfProtection=true` and `server.enableCORS=true`. Do not turn
them off to make proxying appear to work.

Forward the original host **including any non-default port** with `$http_host`,
and forward the public scheme. Configure Streamlit's public browser address and,
when required, `server.corsAllowedOrigins` to the exact approved URL. A real
WebSocket handshake through the public URL must prove the origin configuration;
an HTTP health response alone is insufficient.

### 4. Upload limits

Streamlit's application limit applies to a file, while nginx limits the complete
multipart request body. Therefore the proxy limit must be higher than the app
limit. For an app limit of 200 MiB, use a 210 MiB proxy limit as the starting
configuration and verify both:

- a supported near-limit PDF succeeds;
- a request above the approved limit fails visibly without partial intake data.

### 5. Forwarded headers

At minimum set:

- `Host $http_host`;
- `X-Forwarded-Host $http_host`;
- `X-Forwarded-For $remote_addr` at the trusted edge;
- `X-Forwarded-Proto $scheme`;
- `X-Forwarded-Port $server_port`.

EIDP must never treat client-supplied `X-Forwarded-For` as authentication. At the
trusted ingress, ICT must replace it with the verified immediate client address,
not append an untrusted client-supplied chain. If a trusted upstream load
balancer exists, ICT must first configure an explicit trusted-proxy/real-IP
policy and document the resulting public scheme, port and client-address chain.

### 6. Health endpoint

`/_stcore/health` (or `/eidp/_stcore/health`) must have an explicit policy:

- either a separate exact-match location restricted to the ICT monitoring
  source; or
- a probe that supplies the same institutional authentication as users.

It must not be accidentally blocked by a blanket `auth_request`, and it must not
be opened beyond the approved internal monitoring boundary. The endpoint is a
liveness signal only and returns no identity or secret data.

### 7. Trusted identity is fail-closed

Application support for trusted proxy identity and configured fallback is **AVAILABLE**.
The launcher validates the selected mode before Streamlit starts, trusted mode
requires a non-empty proxy secret, and every served application request resolves
one typed identity. ICT configuration and acceptance evidence remain **PENDING
and release blocking**.

When trusted mode is enabled:

1. ICT authenticates the request and derives a stable user ID.
2. ICT overwrites any client-supplied identity header with the verified value.
3. ICT injects a second shared-secret header using its secret-management
   mechanism.
4. EIDP validates identity plus secret using constant-time comparison.
5. Missing configuration prevents application startup; except for the dedicated
   liveness endpoint, missing/invalid values reject the entire application
   request and never downgrade to a read-only view or fallback.

Agreed header names are `X-Auth-User` and `X-EIDP-Proxy-Secret`. Neither the
secret nor its hash may enter git, logs, screenshots, HAR files, audit content or
the deployment manifest.

If ICT cannot supply a stable user ID, **AVAILABLE application support** allows
an explicit `configured_fallback` mode for the v1 pilot. In that mode the app
ignores all identity headers and records the configured operator plus
`identity_source=configured_fallback`; this limitation must appear in PI
acceptance evidence. It also explicitly trusts every Venus local account capable
of reaching loopback not to bypass the proxy. If PI does not accept that trust
assumption, fallback is disabled and trusted mode is mandatory.

## Illustrative nginx Application Location

This is not a drop-in institution configuration. The `map` directive belongs in
the nginx `http` context, and ICT must confirm that the auth-request module is
available. ICT must bind the verified identity and `$eidp_proxy_secret` variable
through its own authentication and secret systems.

```nginx
map $http_upgrade $connection_upgrade {
    default upgrade;
    ''      close;
}

location / {
    auth_request /auth;
    auth_request_set $eidp_verified_user $upstream_http_x_user_id;

    proxy_pass http://127.0.0.1:8502;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection $connection_upgrade;

    proxy_set_header Host $http_host;
    proxy_set_header X-Forwarded-Host $http_host;
    proxy_set_header X-Forwarded-For $remote_addr;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-Port $server_port;

    proxy_set_header X-Auth-User $eidp_verified_user;
    proxy_set_header X-EIDP-Proxy-Secret $eidp_proxy_secret;

    client_max_body_size 210m;
    proxy_read_timeout 3600s;
    proxy_buffering off;
}
```

For sub-path hosting, ICT must add the `/eidp` to `/eidp/` redirect and change
the application location to `/eidp/` without stripping the prefix. The health
policy is a separate exact-match location or authenticated probe as specified
above.

The example assumes this nginx instance terminates public TLS. If a trusted
upstream load balancer terminates TLS, ICT must use verified fixed/upstream
scheme and port values instead of blindly forwarding this nginx instance's
`$scheme` and `$server_port`.

## ICT Acceptance Checklist

- [ ] Exact internal HTTPS URL and root/sub-path decision recorded
- [ ] TLS and business-network allowlist active
- [ ] HTTP/1.1 WebSocket upgrade succeeds on `_stcore/stream`
- [ ] public Host/port/scheme and Streamlit origin settings agree
- [ ] XSRF and CORS remain enabled
- [ ] proxy body limit exceeds app file limit; near-limit tests recorded
- [ ] read timeout and buffering behavior verified with a live session
- [ ] forwarded headers overwritten at the trusted ingress
- [ ] health endpoint follows its explicit monitoring policy
- [ ] stable per-user ID capability confirmed or fallback limitation recorded
- [ ] trusted mode secret is injected from ICT secret management and never captured
- [ ] business PC completes upload, review and download through the proxy
- [ ] off-host backup pull and receipt path identified

## Authoritative References

- [Streamlit architecture and WebSocket sessions](https://docs.streamlit.io/develop/concepts/architecture/architecture)
- [Streamlit configuration options](https://docs.streamlit.io/develop/api-reference/configuration/config.toml)
- [nginx WebSocket proxying](https://nginx.org/en/docs/http/websocket.html)
- [nginx proxy module](https://nginx.org/en/docs/http/ngx_http_proxy_module.html)
- [nginx auth request module](https://nginx.org/en/docs/http/ngx_http_auth_request_module.html)
