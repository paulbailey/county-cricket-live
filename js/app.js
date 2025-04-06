import Alpine from 'alpinejs'
import persist from '@alpinejs/persist'

// Register the stream component with Alpine
Alpine.data('stream', () => ({
    autoplayEnabled: Alpine.$persist(false).as('autoplayEnabled').using(localStorage),
    competitions: {},
    players: new Map(),
    apiReady: false,
    playersInitialized: false,
    metadataLoaded: false,
    scores: {},
    scoresLastUpdated: null,

    formatLocalTime(gmtTime) {
        if (!gmtTime) return '';

        // Parse the GMT time (HH:MM:SS)
        const [hours, minutes] = gmtTime.split(':');

        // Create a date object for today with the GMT time
        const today = new Date();
        const gmtDate = new Date(Date.UTC(
            today.getUTCFullYear(),
            today.getUTCMonth(),
            today.getUTCDate(),
            parseInt(hours),
            parseInt(minutes),
            0
        ));

        // Format in local time
        return gmtDate.toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit',
            hour12: false,
            timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone
        });
    },

    async init() {
        // Load initial data immediately
        await Promise.all([
            this.loadStreamData(),
            this.loadScores()
        ]);

        this.metadataLoaded = true;

        // Set up periodic updates
        setInterval(() => this.loadStreamData(), 5 * 60 * 1000);
        setInterval(() => this.loadScores(), 60 * 1000); // Update scores every minute

        // Load YouTube IFrame API
        if (!window.YT) {
            const tag = document.createElement('script');
            tag.src = "https://www.youtube.com/iframe_api";
            const firstScriptTag = document.getElementsByTagName('script')[0];
            firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);

            // Define the global callback for the API
            window.onYouTubeIframeAPIReady = () => {
                console.log('YouTube IFrame API Ready');
                this.apiReady = true;
                this.initializePlayers();
            };
        } else {
            this.apiReady = true;
            this.initializePlayers();
        }
    },

    initializePlayers() {
        if (!this.apiReady || this.playersInitialized) {
            return;
        }

        console.log('Initializing players...');
        this.playersInitialized = true;

        // Initialize players for all live streams across all competitions
        Object.values(this.competitions).forEach(competition => {
            competition.live.forEach(stream => {
                if (stream.videoId && !this.players.has(stream.videoId)) {
                    console.log(`Creating player for video ${stream.videoId}`);
                    new YT.Player(`player-${stream.videoId}`, {
                        videoId: stream.videoId,
                        playerVars: {
                            'mute': 1
                        },
                        events: {
                            'onReady': (event) => this.onPlayerReady(stream.videoId, event)
                        }
                    });
                }
            });
        });
    },

    async loadStreamData() {
        try {
            const response = await fetch(`data/streams.json?t=${Date.now()}`);
            const data = await response.json();

            // Remove lastUpdated from the data
            const { lastUpdated, ...competitions } = data;

            // Add matches from scores that aren't in streams
            Object.entries(this.scores).forEach(([matchId, match]) => {
                if (matchId === 'lastUpdated') return;

                // Find the competition this match belongs to
                const competitionName = match.matchType === 'test' ?
                    (match.teams[0].includes('Division One') ? 'County Championship Division One' : 'County Championship Division Two') :
                    'T20 Blast';

                if (!competitions[competitionName]) {
                    competitions[competitionName] = { live: [], upcoming: [] };
                }

                // Check if this match is already in the competition
                const isInCompetition = [...competitions[competitionName].live, ...competitions[competitionName].upcoming]
                    .some(stream => stream.fixture?.match_id === matchId);

                if (!isInCompetition) {
                    // Add the match to the competition's upcoming array
                    if (!competitions[competitionName].upcoming) {
                        competitions[competitionName].upcoming = [];
                    }
                    competitions[competitionName].upcoming.push({
                        fixture: {
                            match_id: matchId,
                            home_team: match.teams[0],
                            away_team: match.teams[1],
                            venue: match.venue,
                            start_time_gmt: match.dateTimeGMT?.split('T')[1]?.split('.')[0],
                            day: match.status?.split(':')[0]
                        }
                    });
                }
            });

            // Only update if there are changes or this is the first load
            if (Object.keys(competitions).length > 0 || !this.metadataLoaded) {
                this.competitions = competitions;
                this.metadataLoaded = true;

                // Reinitialize players if needed
                if (this.apiReady) {
                    this.playersInitialized = false;
                    this.initializePlayers();
                }
            }
        } catch (error) {
            console.error('Error loading stream data:', error);
        }
    },

    async loadScores() {
        try {
            const response = await fetch(`data/scores.json?t=${Date.now()}`);
            const data = await response.json();
            // Extract lastUpdated from the data
            const { lastUpdated, ...matches } = data;
            this.scores = matches;
            this.scoresLastUpdated = lastUpdated;
        } catch (error) {
            console.error('Error loading scores:', error);
        }
    },

    formatTimestamp(timestamp) {
        if (!timestamp) return '';
        const date = new Date(timestamp);
        return date.toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit',
            hour12: false,
            timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone
        });
    },

    getMatchScore(matchId) {
        const match = this.scores[matchId];
        if (!match) return null;

        let scoreText = `<strong>${match.status || ''}</strong>`;

        // Add scores for each innings in reverse order
        if (match.score && match.score.length > 0) {
            [...match.score].reverse().forEach(inning => {
                // Convert inning number to ordinal
                const inningNum = inning.inning.match(/\d+/)[0];
                const ordinal = inningNum === '1' ? '1st' : '2nd';
                const teamName = inning.inning.split(' Inning')[0];

                // Format the score, using "all out" if all wickets are lost
                const score = parseInt(inning.w) === 10 ? `${inning.r} all out` : `${inning.r}/${inning.w}`;
                scoreText += `<br>${teamName} ${ordinal} Innings: ${score} (${inning.o} overs)`;
            });
        }

        return scoreText;
    },

    isMatchInStreams(matchId) {
        // Check if the match is in any competition's live or upcoming arrays
        return Object.values(this.competitions).some(competition => {
            const allMatches = [...(competition.live || []), ...(competition.upcoming || [])];
            return allMatches.some(stream => {
                // Check both match_id and match_url for compatibility
                const streamMatchId = stream.fixture?.match_id || stream.fixture?.match_url;
                return streamMatchId === matchId;
            });
        });
    },

    onPlayerReady(videoId, event) {
        console.log(`Player ready for video ${videoId}`);
        this.players.set(videoId, event.target);

        // Set initial autoplay state
        if (this.autoplayEnabled) {
            console.log(`Starting video ${videoId} due to autoplay being enabled`);
            event.target.playVideo();
            // Mute after a short delay to ensure the player is playing
            setTimeout(() => {
                event.target.mute();
            }, 1000);
        }
    },

    toggleAllPlayers() {
        if (!this.apiReady) {
            console.log('YouTube API not ready yet, waiting...');
            return;
        }

        console.log(`Toggling all players. Autoplay enabled: ${this.autoplayEnabled}`);
        console.log(`Number of players: ${this.players.size}`);

        const playVideo = (player) => {
            if (player && typeof player.playVideo === 'function') {
                console.log('Playing video');
                player.playVideo();
                // Mute after a short delay to ensure the player is playing
                setTimeout(() => {
                    player.mute();
                }, 1000);
            } else {
                console.log('Player or playVideo function not available');
            }
        };

        const pauseVideo = (player) => {
            if (player && typeof player.pauseVideo === 'function') {
                console.log('Pausing video');
                player.unMute();
                player.pauseVideo();
            } else {
                console.log('Player or pauseVideo function not available');
            }
        };

        // Toggle all players based on the autoplay setting
        this.players.forEach((player, videoId) => {
            console.log(`Processing player for video ${videoId}`);
            if (this.autoplayEnabled) {
                playVideo(player);
            } else {
                pauseVideo(player);
            }
        });
    },

    formatTimeUntil(scheduledTime) {
        if (!scheduledTime) return '';

        const now = new Date();
        const scheduled = new Date(scheduledTime);
        const diff = scheduled - now;

        if (diff < 0) return 'Started';

        const hours = Math.floor(diff / (1000 * 60 * 60));
        const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));

        if (hours > 0) {
            return `Starts in ${hours}h ${minutes}m`;
        }
        return `Starts in ${minutes}m`;
    },

    formatDescription(description) {
        if (!description) return '';

        // Convert newlines to <br> tags
        let formatted = description.replace(/\n/g, '<br>');

        // Wrap URLs in <a> tags
        const urlRegex = /(https?:\/\/[^\s<]+)/g;
        formatted = formatted.replace(urlRegex, '<a href="$1" target="_blank" rel="noopener noreferrer" class="link link-hover">$1</a>');

        return formatted;
    },

    shouldCollapseDescription(description) {
        if (!description) return false;
        // Count the number of line breaks and characters
        const lineBreaks = (description.match(/\n/g) || []).length;
        const charCount = description.length;
        // Collapse if more than 1 line break or more than 100 characters
        return lineBreaks > 1 || charCount > 100;
    }
}))

// Initialize Alpine
Alpine.plugin(persist)
Alpine.start()

function displayStreams(streams) {
    const container = document.getElementById('streams-container');
    container.innerHTML = '';

    // Sort competitions alphabetically
    const sortedCompetitions = Object.keys(streams)
        .filter(key => key !== 'lastUpdated')
        .sort();

    sortedCompetitions.forEach(competition => {
        const compData = streams[competition];
        if (!compData.live || compData.live.length === 0) return;

        // Sort live streams by home team
        const sortedStreams = [...compData.live].sort((a, b) => {
            const teamA = a.fixture?.home_team || '';
            const teamB = b.fixture?.home_team || '';
            return teamA.localeCompare(teamB);
        });

        const compDiv = document.createElement('div');
        compDiv.className = 'mb-8';
        compDiv.innerHTML = `
            <h2 class="text-2xl font-bold mb-4">${competition}</h2>
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                ${sortedStreams.map(stream => `
                    <div class="bg-white rounded-lg shadow-md overflow-hidden">
                        <div class="aspect-w-16 aspect-h-9">
                            <iframe
                                class="w-full h-full"
                                src="https://www.youtube.com/embed/${stream.videoId}?enablejsapi=1&origin=${encodeURIComponent(window.location.origin)}&autoplay=${autoplayEnabled ? '1' : '0'}&mute=1"
                                frameborder="0"
                                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                                allowfullscreen
                            ></iframe>
                        </div>
                        <div class="p-4">
                            <h3 class="text-lg font-semibold mb-2">${stream.fixture.home_team} vs ${stream.fixture.away_team}</h3>
                            <p class="text-gray-600">${stream.fixture.venue}</p>
                            <p class="text-gray-600">${formatLocalTime(stream.fixture.start_date)}</p>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
        container.appendChild(compDiv);
    });
}