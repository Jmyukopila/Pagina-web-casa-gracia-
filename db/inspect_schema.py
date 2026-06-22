"""
Dump the current public-schema tables, columns, types, and constraints.
Run BEFORE migrating so we alter with full knowledge of what's there.

    python db/inspect.py
"""
import asyncio
from _common import connect


async def main():
    con = await connect()
    try:
        ver = await con.fetchval("select version()")
        print("Connected:", ver.split(",")[0], "\n")

        tables = await con.fetch("""
            select table_name from information_schema.tables
            where table_schema='public' and table_type='BASE TABLE'
            order by table_name
        """)
        if not tables:
            print("(no hay tablas en el schema public)")
        for t in tables:
            name = t["table_name"]
            print(f"== {name} ==")
            cols = await con.fetch("""
                select column_name, data_type, character_maximum_length,
                       is_nullable, column_default
                from information_schema.columns
                where table_schema='public' and table_name=$1
                order by ordinal_position
            """, name)
            for c in cols:
                typ = c["data_type"]
                if c["character_maximum_length"]:
                    typ += f"({c['character_maximum_length']})"
                nn = "" if c["is_nullable"] == "YES" else " NOT NULL"
                dflt = f" default {c['column_default']}" if c["column_default"] else ""
                print(f"   {c['column_name']:<16} {typ}{nn}{dflt}")
            # constraints
            cons = await con.fetch("""
                select tc.constraint_type, kcu.column_name,
                       ccu.table_name as ref_table, ccu.column_name as ref_col
                from information_schema.table_constraints tc
                left join information_schema.key_column_usage kcu
                  on tc.constraint_name=kcu.constraint_name
                left join information_schema.constraint_column_usage ccu
                  on tc.constraint_name=ccu.constraint_name and tc.constraint_type='FOREIGN KEY'
                where tc.table_schema='public' and tc.table_name=$1
                order by tc.constraint_type
            """, name)
            for k in cons:
                if k["constraint_type"] == "FOREIGN KEY":
                    print(f"   FK  {k['column_name']} -> {k['ref_table']}.{k['ref_col']}")
                elif k["constraint_type"] == "PRIMARY KEY":
                    print(f"   PK  {k['column_name']}")
            # row count
            try:
                cnt = await con.fetchval(f'select count(*) from "{name}"')
                print(f"   rows: {cnt}")
            except Exception:
                pass
            print()
    finally:
        await con.close()


if __name__ == "__main__":
    asyncio.run(main())
