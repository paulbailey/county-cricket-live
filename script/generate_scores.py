import asyncio
import json
from pathlib import Path
from cricapi_client import CricAPIClient
from models import StreamsData

async def main():
    try:
        # Initialize the client
        client = CricAPIClient()

        # Read streams data
        streams_file = Path(__file__).parent.parent / 'public' / 'data' / 'streams.json'
        with open(streams_file, 'r', encoding='utf-8') as f:
            streams_data = StreamsData(**json.load(f))

        # Generate matches data
        matches_data = await client.generate_matches_data(streams_data)

        # Write matches.json
        matches_file = Path(__file__).parent.parent / 'public' / 'data' / 'matches.json'
        with open(matches_file, 'w', encoding='utf-8') as f:
            json.dump(matches_data.model_dump(), f, indent=2, default=str)
        print('Successfully generated matches.json')

    except Exception as e:
        print(f'Error generating matches.json: {e}')
        exit(1)

if __name__ == '__main__':
    asyncio.run(main()) 