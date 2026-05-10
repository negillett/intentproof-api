# Examples

Runnable scripts for calling a local or deployed **`intentproof-api`**. Set **`INTENTPROOF_API_BASE`** (default `http://127.0.0.1:8000`) and **`INTENTPROOF_API_KEY`** to match your **`INTENTPROOF_API_KEYS`** mapping.

**`INTENTPROOF_API_BASE`** is validated by **`examples/http_utils.require_http_base`**. Use an **`http://`** or **`https://`** URL with a hostname. Do not embed **username or password** in the URL (use **`X-API-Key`** or other headers for auth). You may include a **path prefix** when the API is mounted below the host root (for example `https://ingress.example.com/tenant-a/intentproof`); trailing slashes on that prefix are normalized. Do not include a query string or fragment. Scripts append **`/v1/events`** (and correlation routes) under that base.

| Script | Description |
| --- | --- |
| **`curl_ingest_event.sh`** | **`POST /v1/events`** with **`curl`** |
| **`curl_query_correlation.sh`** | **`GET /v1/events/by-correlation/{id}`** with **`curl`** — path segment is URL-encoded (**`INTENTPROOF_CORRELATION_ID`**) |
| **`python_sdk_http_exporter.py`** | **[intentproof-sdk-python](https://github.com/IntentProof/intentproof-sdk-python)** **`HttpExporter`** with a flat wire body — requires **`intentproof`** installed (see below) |
| **`python_print_http_status.py`** | Same JSON as ingest via **`urllib`**; prints HTTP status (stdlib only) |

Shell examples require **`curl`** and pass **`curl -f`** so HTTP **4xx** / **5xx** yield a non-zero exit status. The direct POST example uses Python’s standard library only and exits non-zero when the status code is **≥ 400**.

## Python SDK (`intentproof-sdk-python`)

**`python_sdk_http_exporter.py`** imports the real **`intentproof`** package from [intentproof-sdk-python](https://github.com/IntentProof/intentproof-sdk-python). Install it in your environment (dependencies included):

```bash
# Typical ~/src layout: repos are siblings
pip install -e ../intentproof-sdk-python
```

Or use PyPI:

```bash
pip install intentproof-sdk
```

Optional: set **`INTENTPROOF_SDK_PYTHON_ROOT`** to the root of an **`intentproof-sdk-python`** checkout. The script prepends **`$INTENTPROOF_SDK_PYTHON_ROOT/src`** to **`sys.path`** so that tree is imported first. You still need package dependencies available — **`pip install -e "$INTENTPROOF_SDK_PYTHON_ROOT"`** is the usual way to satisfy them while working against that checkout.

Pin **`intentproof-sdk`** to a release compatible with this API’s **`[tool.intentproof]`** pins in **`pyproject.toml`**.

## Security notes (examples are trusted-operator scripts)

- **`INTENTPROOF_API_BASE`** / **`INTENTPROOF_API_KEYS`** — Treat like secrets-adjacent configuration: point **`BASE_URL`** only at **your** API (**`http://`** / **`https://`**), optionally with a **path prefix** (see above); query/fragment are rejected. **`examples/http_utils.require_http_base`** enforces this in **`curl`** scripts (via **`PYTHONPATH`** to import **`http_utils`**) and in the Python examples; non-HTTP schemes (**`file:`**, etc.) are rejected. Ingest URLs use **`urllib.parse.urljoin`** under the validated base. This does **not** defend against a deliberate operator pointing **`BASE_URL`** at an arbitrary internal host (classic SSRF); keep values under operator control, same as production SDK **`HttpExporter`** guidance.
- **`INTENTPROOF_SDK_PYTHON_ROOT`** — Prepends code from that checkout onto **`sys.path`**. Only set it to a tree you trust (same risk model as **`PYTHONPATH`**).
- **Shell `curl` scripts** — **`API_KEY`** is passed in a quoted header; avoid embedding newline-containing values (HTTP header injection). **`INTENTPROOF_QUERY_LIMIT`** is validated as an integer **1–500** so it cannot inject extra query parameters.
- **`urllib`** — Follows HTTP redirects by default; use a **`BASE_URL`** you trust end-to-end if redirects are a concern.
