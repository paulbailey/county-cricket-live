# County Cricket Live

A simple web application that shows live and upcoming county cricket streams from YouTube. The site automatically updates every 15 minutes during the day to show the latest streams.

## Features

- Live streams from county cricket clubs
- Upcoming scheduled matches
- Automatic updates every 15 minutes during the day
- Mobile-friendly design
- YouTube IFrame API integration for better video control
- Autoplay toggle with persistent preference
- Fallback to YouTube thumbnails for non-embeddable videos
- Clean, modern UI with Tailwind CSS

## How it Works

1. The GitHub Action (`poll-youtube.yml`) runs every 15 minutes during the day (8 AM - 8 PM)
2. It checks each county's YouTube channel for live and upcoming streams
3. The data is saved to `data/streams.json`
4. The site automatically updates to show the latest streams
5. Videos are embedded using the YouTube IFrame API for better control

## Development

### Prerequisites

- Python 3.8+
- YouTube Data API key
- GitHub account for Actions

### Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file with your YouTube API key:
   ```
   YOUTUBE_API_KEY=your_api_key_here
   ```
4. Run the update script:
   ```bash
   python script/update_streams.py
   ```

### Local Development

1. Start a local server:
   ```bash
   python -m http.server 8000
   ```
2. Open http://localhost:8000 in your browser

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

MIT License - see LICENSE file for details