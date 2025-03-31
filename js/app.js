// Alpine.js app
function streamApp() {
    return {
        autoplayEnabled: false,
        liveStreams: [],
        upcomingMatches: [],
        players: new Map(),
        apiReady: false,

        async init() {
            // Load initial data immediately
            await this.loadStreamData();

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
                };
            } else {
                this.apiReady = true;
            }
        },

        async loadStreamData() {
            try {
                const response = await fetch('data/streams.json');
                const data = await response.json();
                this.updateStreams(data);
            } catch (error) {
                console.error('Error loading stream data:', error);
            }
        },

        updateStreams(data) {
            this.liveStreams = data.liveStreams || [];
            this.upcomingMatches = data.upcomingMatches || [];
        },

        onPlayerReady(videoId, event) {
            console.log(`Player ready for video ${videoId}`);
            this.players.set(videoId, event.target);
        },

        formatTimeUntil(startTime) {
            const start = new Date(startTime);
            const now = new Date();
            const diff = start - now;
            const hours = Math.floor(diff / (1000 * 60 * 60));
            const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
            return `Starts in ${hours}h ${minutes}m`;
        }
    }
}
