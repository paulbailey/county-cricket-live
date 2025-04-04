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
        await this.loadStreamData();

        this.metadataLoaded = true;

        // Set up periodic updates
        setInterval(() => this.loadStreamData(), 5 * 60 * 1000);

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
            const response = await fetch('data/streams.json');
            const data = await response.json();

            // Remove lastUpdated from the data
            const { lastUpdated, ...competitions } = data;

            // Update competitions
            this.competitions = competitions;

            // Reinitialize players if needed
            if (this.apiReady) {
                this.playersInitialized = false;
                this.initializePlayers();
            }
        } catch (error) {
            console.error('Error loading stream data:', error);
        }
    },

    onPlayerReady(videoId, event) {
        console.log(`Player ready for video ${videoId}`);
        this.players.set(videoId, event.target);

        // Set initial autoplay state
        if (this.autoplayEnabled) {
            console.log(`Starting video ${videoId} due to autoplay being enabled`);
            event.target.playVideo();
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
            } else {
                console.log('Player or playVideo function not available');
            }
        };

        const pauseVideo = (player) => {
            if (player && typeof player.pauseVideo === 'function') {
                console.log('Pausing video');
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