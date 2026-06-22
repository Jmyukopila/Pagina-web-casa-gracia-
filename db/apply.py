"""
Apply a .sql migration file inside a single transaction. If anything fails,
the whole thing rolls back (nothing changes).

    python db/apply.py migration_001.sql
"""
import asyncio
import sys
from pathlib import Path

from _common import connect

HERE = Path(__file__).resolve().parent


async def main():
    fname = sys.argv[1] if len(sys.argv) > 1 else "migration_001.sql"
    sql = (HERE / fname).read_text(encoding="utf-8")
    con = await connect()
    try:
        async with con.transaction():
            await con.execute(sql)
        print(f"OK: {fname} aplicado correctamente (transaccion confirmada).")
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
        print("La transaccion se revirtio; la base quedo intacta.")
        raise
    finally:
        await con.close()


if __name__ == "__main__":
    asyncio.run(main())
