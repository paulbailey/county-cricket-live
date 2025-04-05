const fs = require('fs');
const path = require('path');
const axios = require('axios');

const CRICKET_API_KEY = process.env.CRICKET_API_KEY;
const STREAMS_FILE = path.join(process.cwd(), 'public', 'data', 'streams.json');
const SCORES_FILE = path.join(process.cwd(), 'public', 'data', 'scores.json');

async function fetchMatchDetails(matchId) {
    try {
        const response = await axios.get(`https://api.cricapi.com/v1/match_info?apikey=${CRICKET_API_KEY}&id=${matchId}`);
        return response.data.data;
    } catch (error) {
        console.error(`Error fetching match details for ${matchId}:`, error.message);
        return null;
    }
}

async function generateScores() {
    try {
        // Read streams.json
        const streamsData = JSON.parse(fs.readFileSync(STREAMS_FILE, 'utf8'));

        // Extract all match IDs
        const matchIds = new Set();
        Object.values(streamsData).forEach(division => {
            if (division.live) {
                division.live.forEach(match => {
                    if (match.fixture?.match_id) {
                        matchIds.add(match.fixture.match_id);
                    }
                });
            }
            if (division.upcoming) {
                division.upcoming.forEach(match => {
                    if (match.fixture?.match_id) {
                        matchIds.add(match.fixture.match_id);
                    }
                });
            }
        });

        // Fetch match details for each match ID
        const scores = {};
        for (const matchId of matchIds) {
            const matchDetails = await fetchMatchDetails(matchId);
            if (matchDetails) {
                scores[matchId] = matchDetails;
            }
        }

        // Add lastUpdated timestamp
        scores.lastUpdated = new Date().toISOString();

        // Write scores.json
        fs.writeFileSync(SCORES_FILE, JSON.stringify(scores, null, 2));
        console.log('Successfully generated scores.json');
    } catch (error) {
        console.error('Error generating scores.json:', error);
        process.exit(1);
    }
}

generateScores(); 