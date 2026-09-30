import asyncio
from src.database.connection import engine

async def test():
    try:
        async with engine.begin() as conn:
            print("Successfully connected to Supabase PostgreSQL!")
    except Exception as e:
        print(f"Error connecting: {e}")
    finally:
        await engine.dispose()

asyncio.run(test())
