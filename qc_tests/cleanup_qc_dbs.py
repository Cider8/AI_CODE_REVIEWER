"""Lists leftover QC databases; with --drop, drops them.
Only names starting with "krishnalens_qc_" are ever touched."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend_fastAPI"))

PREFIX = "krishnalens_qc_"


async def main(drop):
    from motor.motor_asyncio import AsyncIOMotorClient
    from app.config import settings

    client = AsyncIOMotorClient(settings.mongo_uri)
    names = [n for n in await client.list_database_names() if n.startswith(PREFIX)]
    print(f"leftover QC databases: {names or 'none'}")
    if drop:
        for n in names:
            assert n.startswith(PREFIX)
            await client.drop_database(n)
            print(f"dropped {n}")
    client.close()


if __name__ == "__main__":
    asyncio.run(main("--drop" in sys.argv))
