import Alpine from 'alpinejs'
import persist from '@alpinejs/persist'
import morph from '@alpinejs/morph'

// Debounce function to limit the rate at which a function can fire
const debounce = (func, wait) => {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
};

// Register the stream component with Alpine
Alpine.data('stream', () => ({
    autoplayEnabled: Alpine.$persist(false).as('autoplayEnabled').using(localStorage),
    competitions: {},
    rawCompetitions: {},
    players: new Map(),
    apiReady: false,
    playersInitialized: false,
    metadataLoaded: false,
    error: null,

    formatLocalTime(gmtTime) {
        if (!gmtTime) return '';

        try {
            // Parse the GMT time (HH:MM:SS or HH:MM)
            const [hours, minutes] = gmtTime.split(':').map(num => parseInt(num, 10));
            if (isNaN(hours) || isNaN(minutes)) return '';

            // Create a date object for today with the GMT time
            const today = new Date();
            const gmtDate = new Date(Date.UTC(
                today.getUTCFullYear(),
                today.getUTCMonth(),
                today.getUTCDate(),
                hours,
                minutes,
                0
            ));

            // Format in local time
            return gmtDate.toLocaleTimeString([], {
                hour: '2-digit',
                minute: '2-digit',
                hour12: false,
                timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone
            });
        } catch (error) {
            console.error('Error formatting time:', error);
            return '';
        }
    },

    async init() {
        // Load initial data immediately
        await this.loadStreamData();
        this.metadataLoaded = true;

        // Set up periodic updates
        setInterval(() => this.loadStreamData(), 2 * 60 * 1000);

        // Load YouTube IFrame API
        if (!window.YT) {
            console.log('Loading YouTube IFrame API');
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
            console.log('YouTube IFrame API already loaded');
            this.apiReady = true;
            this.initializePlayers();
        }
    },

    initializePlayers: debounce(function () {
        if (!this.apiReady || this.playersInitialized) {
            console.log("apiReady", this.apiReady);
            console.log("playersInitialized", this.playersInitialized);
            console.log('Players already initialized or API not ready');
            return;
        }

        console.log('Initializing players...');
        this.playersInitialized = true;

        Object.values(this.competitions).forEach(competition => {
            competition.live.forEach(stream => {
                if (stream.videoId && !this.players.has(stream.videoId)) {
                    try {
                        console.log(`Creating player for video ${stream.videoId}`);
                        new YT.Player(`player-${stream.videoId}`, {
                            videoId: stream.videoId,
                            playerVars: {
                                'mute': this.autoplayEnabled ? 1 : 0,
                                'playsinline': 1,
                                'rel': 0
                            },
                            events: {
                                'onReady': (event) => this.onPlayerReady(stream.videoId, event),
                                'onError': (event) => console.error(`Player error for video ${stream.videoId}:`, event)
                            }
                        });
                    } catch (error) {
                        console.error(`Failed to initialize player for video ${stream.videoId}:`, error);
                    }
                }
            });
        });
    }, 500),

    async loadStreamData() {
        try {
            this.error = null;
            const response = await fetch(`data/matches.json?t=${Date.now()}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();

            // Extract lastUpdated and competitions from the data
            const { lastUpdated, competitions } = data;

            // Only update if there are changes or this is the first load
            if (Object.keys(competitions).length > 0 || !this.metadataLoaded) {
                // Store the raw competition data
                this.rawCompetitions = competitions;

                // Transform the matches data into the expected format
                const transformedCompetitions = {};

                Object.entries(competitions).forEach(([compName, comp]) => {
                    transformedCompetitions[compName] = {
                        live: [],
                        upcoming: []
                    };

                    comp.matches.forEach(match => {
                        const streamData = {
                            videoId: match.stream?.videoId,
                            title: match.stream?.title,
                            channelId: match.stream?.channelId,
                            matchEnded: match.matchEnded,
                            fixture: {
                                match_id: match.id,
                                home_team: match.homeTeam,
                                away_team: match.awayTeam,
                                venue: match.venue,
                                start_time_gmt: match.startTime || null,
                                day: match.status?.split(' - ')?.[0]
                            }
                        };

                        // Add to live array if there's a videoId, otherwise to upcoming
                        if (match.stream?.videoId) {
                            transformedCompetitions[compName].live.push(streamData);
                        } else {
                            transformedCompetitions[compName].upcoming.push(streamData);
                        }
                    });

                    // Sort matches by home team, with ended matches last
                    transformedCompetitions[compName].live.sort((a, b) => {
                        if (a.matchEnded && !b.matchEnded) return 1;
                        if (!a.matchEnded && b.matchEnded) return -1;
                        return a.fixture.home_team.localeCompare(b.fixture.home_team);
                    });
                    transformedCompetitions[compName].upcoming.sort((a, b) => {
                        if (a.matchEnded && !b.matchEnded) return 1;
                        if (!a.matchEnded && b.matchEnded) return -1;
                        return a.fixture.home_team.localeCompare(b.fixture.home_team);
                    });
                });

                this.competitions = transformedCompetitions;
                this.metadataLoaded = true;

                // Reinitialize players if needed
                if (this.apiReady) {
                    this.playersInitialized = false;
                    this.initializePlayers();
                }
            }
        } catch (error) {
            console.error('Error loading stream data:', error);
            this.error = 'Failed to load match data. Please try refreshing the page.';
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
        // Find the match in raw competitions data
        let match = null;
        for (const comp of Object.values(this.rawCompetitions)) {
            match = comp.matches.find(m => m.id === matchId);
            if (match) break;
        }
        if (!match) return null;

        let scoreText = `<strong>${match.status || ''}</strong>`;

        // Add scores for each innings in reverse order
        if (match.scores?.innings && match.scores.innings.length > 0) {
            [...match.scores.innings].reverse().forEach(inning => {
                // Extract team name and innings number
                const [teamName, inningNum] = inning.innings.split(' Inning ');

                // Convert number to ordinal
                const ordinal = inningNum === '1' ? '1st' : '2nd';

                // Format the score, using "all out" if all wickets are lost
                const score = parseInt(inning.wickets) === 10 ? `${inning.runs} all out` : `${inning.runs}/${inning.wickets}`;
                scoreText += `<br>${teamName} ${ordinal} Innings: ${score} (${inning.overs} overs)`;
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
Alpine.plugin(morph)
Alpine.start()
