import asyncio
from app.database import init_db
from app.models.flight_result import FlightResult
from app.models.provider_xpath import ProviderXPath
from app.models.search_log import SearchLog

async def main():
    print("Creating tables in PostgreSQL...")
    await init_db()
    print("Tables created successfully!")

if __name__ == "__main__":
    asyncio.run(main())
