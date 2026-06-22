"""
The direct host (db.<ref>.supabase.co) doesn't resolve here, so find the
correct Supabase *pooler* endpoint by trying each regional host with the
pooler username (postgres.<ref>). On success, rewrite DATABASE_URL in the
root .env to the working Session-pooler URL.

    python db/find_region.py
"""
import asyncio
import re
from pathlib import Path
from urllib.parse import urlparse, quote

import asyncpg
from _common import get_dsn

ROOT = Path(__file__).resolve().parent.parent
ENV = ROOT / ".env"

# Ordered by likelihood for a Colombia/LATAM project, then the rest.
REGIONS = [
    "us-east-1", "us-east-2", "sa-east-1", "us-west-1", "us-west-2",
    "ca-central-1", "eu-west-1", "eu-west-2", "eu-west-3", "eu-central-1",
    "eu-central-2", "eu-north-1", "ap-southeast-1", "ap-southeast-2",
    "ap-south-1", "ap-northeast-1", "ap-northeast-2", "ap-southeast-3",
]
PREFIXES = ["aws-0", "aws-1"]


def parts():
    u = urlparse(get_dsn())
    # ref = the project id, taken from the direct host db.<ref>.supabase.co
    m = re.search(r"db\.([a-z0-9]+)\.supabase\.co", u.hostname or "")
    ref = m.group(1) if m else (u.username or "").replace("postgres.", "")
    return ref, u.password


async def try_host(ref, pwd, host):
    dsn = f"postgresql://postgres.{ref}:{quote(pwd, safe='')}@{host}:5432/postgres"
    try:
        con = await asyncpg.connect(dsn, ssl="require", timeout=8,
                                    statement_cache_size=0)
        await con.fetchval("select 1")
        await con.close()
        return dsn
    except Exception as e:
        return None if "auth" not in str(e).lower() else "AUTHFAIL:" + str(e)


async def main():
    ref, pwd = parts()
    if not ref or not pwd:
        raise SystemExit("No pude extraer ref/password del DATABASE_URL actual.")
    print(f"ref = {ref} ; probando endpoints de pooler...\n")
    for region in REGIONS:
        for pre in PREFIXES:
            host = f"{pre}-{region}.pooler.supabase.com"
            res = await try_host(ref, pwd, host)
            if isinstance(res, str) and res.startswith("AUTHFAIL"):
                print(f"  {host:48} -> host correcto pero AUTH falla: revisa la contraseña")
                return
            if res:
                print(f"  {host:48} -> OK  (region encontrada!)")
                # rewrite DATABASE_URL in .env
                masked = res.replace(quote(pwd, safe=''), "****")
                lines = ENV.read_text(encoding="utf-8").splitlines()
                out, replaced = [], False
                for ln in lines:
                    if ln.strip().startswith("DATABASE_URL="):
                        out.append("DATABASE_URL=" + res); replaced = True
                    else:
                        out.append(ln)
                if not replaced:
                    out.append("DATABASE_URL=" + res)
                ENV.write_text("\n".join(out) + "\n", encoding="utf-8")
                print(f"\n.env actualizado -> {masked}")
                return
            print(f"  {host:48} -> no")
    print("\nNo encontre la region. Copia el string del 'Session pooler' del dashboard.")


if __name__ == "__main__":
    asyncio.run(main())
