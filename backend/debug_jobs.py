import asyncio
from app.database import AsyncSessionLocal
from app.models.job import Job
from sqlalchemy import select


async def main():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Job))
        jobs = result.scalars().all()
        print(f"Jobs in DB: {len(jobs)}")
        for j in jobs:
            print(f"  {j.id[:12]}... status={j.status} file={j.original_filename}")


if __name__ == "__main__":
    asyncio.run(main())
