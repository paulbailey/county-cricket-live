# County Cricket Live

A website providing live streams and upcoming matches from all 18 first-class county cricket clubs in England.

## Overview

County Cricket Live aggregates live streams and upcoming matches from all first-class county cricket clubs in England. The website provides a central hub for cricket fans to access live coverage of county matches.

## Features

- Live stream embeds for current matches
- Upcoming matches section
- County-specific pages
- Mobile-responsive design
- Dark/light mode support

## Technical Details

This is a static website hosted on GitHub Pages. The live stream data is updated via a GitHub Action that runs every 15 minutes to check for new streams and upcoming matches using the YouTube Data API.

## Development

The website is built using:
- HTML5
- CSS3 (with Tailwind CSS)
- JavaScript (Vanilla)
- GitHub Actions for data updates

## Local Development

1. Clone the repository
2. Install dependencies:
   ```bash
   npm install
   ```
3. Run the development server:
   ```bash
   npm run dev
   ```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - see LICENSE file for details