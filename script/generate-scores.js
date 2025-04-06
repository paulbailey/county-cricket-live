import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import axios from 'axios';
import dotenv from 'dotenv';

// Load environment variables from .env file
dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const CRICKET_API_KEY = process.env.CRICKET_API_KEY;
if (!CRICKET_API_KEY) {
    console.error('CRICKET_API_KEY not found in environment variables');
    process.exit(1);
}

const STREAMS_FILE = path.join(__dirname, '..', 'public', 'data', 'streams.json');
const MATCHES_FILE = path.join(__dirname, '..', 'public', 'data', 'matches.json');
const FIXTURES_DIR = path.join(__dirname, '..', 'public', 'data', 'fixtures');

function loadFixtures() {
    const today = new Date().toISOString().split('T')[0];
    const fixturesFile = path.join(FIXTURES_DIR, `${today}.json`);

    try {
        return JSON.parse(fs.readFileSync(fixturesFile, 'utf8'));
    } catch (error) {
        console.error(`Error loading fixtures: ${error.message}`);
        return [];
    }
}

async function fetchMatchDetails(matchId) {
    try {
        const response = await axios.get(`https://api.cricapi.com/v1/match_info?apikey=${CRICKET_API_KEY}&id=${matchId}`);
        return response.data.data;
    } catch (error) {
        console.error(`Error fetching match details for ${matchId}:`, error.message);
        return null;
    }
}

async function generateMatches() {
    try {
        // Read streams.json and fixtures
        const streamsData = JSON.parse(fs.readFileSync(STREAMS_FILE, 'utf8'));
        const fixtures = loadFixtures();

        // Initialize matches structure
        const matches = {
            lastUpdated: new Date().toISOString(),
            competitions: {}
        };

        // Process all streams
        for (const [matchId, stream] of Object.entries(streamsData.streams)) {
            // Find corresponding fixture
            const fixture = fixtures.find(f => f.match_id === matchId);
            if (!fixture) {
                console.warn(`No fixture found for match ${matchId}`);
                continue;
            }

            // Get match details from API
            const matchDetails = await fetchMatchDetails(matchId);

            // Create match entry
            const matchData = {
                id: matchId,
                venue: fixture.venue,
                startTime: fixture.start_time,
                homeTeam: fixture.home_team,
                awayTeam: fixture.away_team,
                scores: matchDetails?.score || null,
                status: matchDetails?.status || 'upcoming',
                stream: {
                    videoId: stream.videoId,
                    title: stream.title,
                    channelId: stream.channelId
                },
                matchStarted: matchDetails?.matchStarted,
                matchEnded: matchDetails?.matchEnded
            };

            // Add to competition group
            const competition = fixture.competition;
            if (!matches.competitions[competition]) {
                matches.competitions[competition] = {
                    name: competition,
                    matches: []
                };
            }
            matches.competitions[competition].matches.push(matchData);
        }

        // Sort matches within each competition by home team
        for (const competition of Object.values(matches.competitions)) {
            competition.matches.sort((a, b) => a.homeTeam.localeCompare(b.homeTeam));
        }

        // Sort competitions alphabetically and create new ordered object
        const orderedCompetitions = {};
        Object.keys(matches.competitions)
            .sort()
            .forEach(key => {
                orderedCompetitions[key] = matches.competitions[key];
            });
        matches.competitions = orderedCompetitions;

        // Write matches.json
        fs.writeFileSync(MATCHES_FILE, JSON.stringify(matches, null, 2));
        console.log('Successfully generated matches.json');
    } catch (error) {
        console.error('Error generating matches.json:', error);
        process.exit(1);
    }
}

generateMatches(); 