import os, csv, json, io, urllib.request, urllib.error, xml.etree.ElementTree as ET
from datetime import datetime, timezone
import logging
import boto3

# ---------------- logging (CloudWatch) ----------------
logger = logging.getLogger()
logger.setLevel(logging.INFO)  # <- ensures logs show in CloudWatch

# ---------------- defaults (will be overridden by secret) ----------------
API_VERSION = "3.19"      # fallback if not provided in secret
VERIFY_SSL = True         # fallback if not provided in secret
HARD_CODED_PREFIX = "tableau"  # top-level S3 folder

# ---------------- AWS clients ----------------
secrets = boto3.client("secretsmanager")
s3 = boto3.client("s3")

NS = {"t": "http://tableau.com/api"}

# ---------------- helpers ----------------
def _get_secret_json(name_or_arn: str) -> dict:
    res = secrets.get_secret_value(SecretId=name_or_arn)
    val = res.get("SecretString")
    if not val and "SecretBinary" in res:
        val = res["SecretBinary"].decode("utf-8")
    return json.loads(val or "{}")

def _to_bool(val, default=True) -> bool:
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.strip().lower() in ("1", "true", "yes", "y", "on")
    return default

def _http_request(method: str, url: str, headers: dict, body: bytes | None, timeout=30):
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    ctx = None
    if not VERIFY_SSL:
        import ssl
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
            return resp.status, resp.headers.get("Content-Type", ""), resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        ctype = e.headers.get("Content-Type", "") if e.headers else ""
        text = e.read().decode("utf-8", errors="replace")
        return e.code, ctype, text

def _api_base(server: str) -> str:
    return f"https://{server}/api/{API_VERSION}"

# ---------------- Tableau REST ----------------
def signin(server: str, pat_name: str, pat_secret: str, site_content_url: str) -> tuple[str, str]:
    url = _api_base(server) + "/auth/signin"
    headers = {"Content-Type": "application/xml", "Accept": "application/xml", "User-Agent": "curl/8.5.0"}
    xml_body = f"""<tsRequest>
  <credentials personalAccessTokenName="{pat_name}"
               personalAccessTokenSecret="{pat_secret}">
    <site contentUrl="{site_content_url}"/>
  </credentials>
</tsRequest>""".encode("utf-8")

    status, ctype, text = _http_request("POST", url, headers, xml_body)
    if status != 200 or "xml" not in (ctype or "").lower():
        raise RuntimeError(f"Sign-in failed: HTTP {status}, Content-Type={ctype}\n{text[:400]}")
    root = ET.fromstring(text)
    cred = root.find(".//t:credentials", NS)
    token = cred.attrib["token"]
    site_id = cred.find("t:site", NS).attrib["id"]
    return token, site_id

def list_site_users(server: str, site_id: str, token: str, page_size: int = 1000) -> list[dict]:
    users, page = [], 1
    while True:
        url = _api_base(server) + f"/sites/{site_id}/users?pageSize={page_size}&pageNumber={page}"
        # JSON first
        status, ctype, text = _http_request("GET", url, {"X-Tableau-Auth": token, "Accept": "application/json"}, None)
        if status == 200 and (ctype or "").lower().startswith("application/json"):
            data = json.loads(text)
            batch = data.get("users", {}).get("user", [])
            users.extend(batch)
            total = int(data.get("pagination", {}).get("totalAvailable", len(batch)))
            if page * page_size >= total or not batch:
                break
            page += 1
            continue
        # XML fallback
        status, ctype, text = _http_request("GET", url, {"X-Tableau-Auth": token, "Accept": "application/xml"}, None)
        if status != 200 or "xml" not in (ctype or "").lower():
            raise RuntimeError(f"/users failed: HTTP {status}, Content-Type={ctype}\n{text[:400]}")
        root = ET.fromstring(text)
        users_node = root.find(".//t:users", NS)
        batch = []
        if users_node is not None:
            for u in users_node.findall("t:user", NS):
                batch.append(u.attrib)
        users.extend(batch)
        if not batch or len(batch) < page_size:
            break
        page += 1
    return users

# ---------------- CSV → S3 ----------------
def write_csv_to_s3(users: list[dict], bucket: str) -> str:
    fields = ["id", "name", "fullName", "siteRole", "lastLogin", "email"]
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields)
    w.writeheader()
    for u in users:
        w.writerow({k: u.get(k, "") for k in fields})
    data = buf.getvalue().encode("utf-8")

    # No site subfolder, no timestamp; always overwrite same key
    key = f"{HARD_CODED_PREFIX}/tableau_server_users.csv"
    s3.put_object(Bucket=bucket, Key=key, Body=data, ContentType="text/csv; charset=utf-8")
    return key


# ---------------- Lambda handler ----------------
def lambda_handler(event, context):
    global API_VERSION, VERIFY_SSL

    # ONLY env vars are the two secret names
    tableau_secret_name = os.environ["TABLEAU_SECRET_NAME"]  # Tableau details + API_VERSION + VERIFY_SSL
    s3_secret_name = os.environ["S3_SECRET_NAME"]            # S3 bucket

    # Load secrets
    tsec = _get_secret_json(tableau_secret_name)
    s3sec = _get_secret_json(s3_secret_name)

    # Pull dynamic runtime config from Tableau secret
    API_VERSION = str(tsec.get("API_VERSION", API_VERSION))          # e.g., "3.19"
    VERIFY_SSL = _to_bool(tsec.get("VERIFY_SSL", VERIFY_SSL), True)  # true/false

    server    = tsec["SERVER"]
    site_slug = tsec.get("SITE_CONTENT_URL", "")
    pat_name  = tsec["PAT_NAME"]
    pat_secret= tsec["PAT_SECRET"]

    bucket = s3sec["S3_BUCKET"]

    logger.info(f"Starting export | server={server} site={site_slug or 'Default'} api_version={API_VERSION} verify_ssl={VERIFY_SSL}")

    token, site_id = signin(server, pat_name, pat_secret, site_slug)
    logger.info("Signed in to Tableau REST API.")

    users = list_site_users(server, site_id, token)
    logger.info(f"Fetched {len(users)} users from site.")

    key = write_csv_to_s3(users, bucket)
    logger.info(f"Wrote CSV to s3://{bucket}/{key}")

    return {"status": "ok", "count": len(users), "bucket": bucket, "key": key, "api_version": API_VERSION}

if __name__ == "__main__":
    print(lambda_handler({}, None))
