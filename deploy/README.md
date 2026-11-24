# Public deployment at adam.entreater.com

## Prerequisites
- A server with Docker and a reverse proxy that routes by host name and obtains
  certificates automatically. `compose.yaml` carries labels for **Traefik** with the Docker
  provider (`exposedbydefault=false`) and a Let's Encrypt resolver named `letsencrypt`.
- A DNS **A record** for the host name pointing to the server. The Let's Encrypt HTTP
  challenge can only succeed once the name resolves:

```bash
dig +short adam.entreater.com      # must return the server's IP address
```

Operator-specific details (server, DNS zone, neighbouring services) are deliberately not
part of this public repository.

## Step 1: Build and start the image
On the server, in the directory of this project:

```bash
cd deploy
IDA_VERSION=$(git -C .. rev-parse --short HEAD) docker compose build
IDA_VERSION=$(git -C .. rev-parse --short HEAD) docker compose up -d
```

The dataset is baked in at build time and verified via SHA-256. Building needs
network, running does not.

## Step 2: Verify
```bash
docker compose ps                                  # status and healthcheck
docker compose logs --tail 50 adam
curl -s https://adam.entreater.com/health          # expects {"status":"ok",...}
```

The certificate may take a few seconds on the first request.

## Requirements for public operation
These points count as requirements for every spec that is published here:

1. **Only public data.** The basis is exclusively the IDC dataset (CC BY 4.0).
   No internal, unpublished or confidential data collections.
2. **Visible attribution.** Every page names source, license and DOI in the footer.
   This is a license obligation, not decoration.
3. **Context notice.** The page makes clear that ADA rates of different
   therapeutics are not comparable without clinical context, and that the presentation
   serves research and makes no medical or regulatory statement.
4. **No confusion with internal tools.** The page does not give the impression of
   containing a company-internal prediction model or unpublished data.
5. **Read-only.** No login, no forms with storage, no write access.
   The container runs with `read_only: true` and without root privileges.
6. **No personal data**, not even in logs. Traefik is already configured
   so that headers and query parameters are not logged.
7. **Limited resources.** 512 MB of memory and 0.5 CPU, because the target server is short
   on memory and has no swap.

## Order in the factory flow
Publishing is **not an agent step**. The factory builds, verifies and delivers
a pull request. After your merge to `main`, deployment happens as a deliberate
step, initially by hand following these instructions. Only once the flow has run
stably for several weeks is automation worthwhile.

Recommended: first make the skeleton public while it only knows `/health`.
Then the chain of DNS, certificate, Traefik and container is proven before the first
domain feature is added.
