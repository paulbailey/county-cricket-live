// Cookie handling functions
function setCookie(name, value, days) {
    let expires = "";
    if (days) {
        const date = new Date();
        date.setTime(date.getTime() + (days * 24 * 60 * 60 * 1000));
        expires = "; expires=" + date.toUTCString();
    }
    document.cookie = name + "=" + (value || "") + expires + "; path=/";
}

function getCookie(name) {
    const nameEQ = name + "=";
    const ca = document.cookie.split(';');
    for (let i = 0; i < ca.length; i++) {
        let c = ca[i];
        while (c.charAt(0) === ' ') c = c.substring(1, c.length);
        if (c.indexOf(nameEQ) === 0) return c.substring(nameEQ.length, c.length);
    }
    return null;
}

// Alpine.js app
function streamApp() {
    return {
        autoplayEnabled: getCookie('autoplayEnabled') === 'true' || false,
        liveStreams: [],
        upcomingMatches: [],
        players: new Map(),
        apiReady: false,

        async init() {
            console.log('Initializing app, autoplay:', this.autoplayEnabled);

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

        toggleAutoplay() {
            this.autoplayEnabled = !this.autoplayEnabled;
            console.log('Toggling autoplay:', this.autoplayEnabled);
            setCookie('autoplayEnabled', this.autoplayEnabled, 365);

            this.players.forEach((player, videoId) => {
                try {
                    if (this.autoplayEnabled) {
                        console.log(`Playing video ${videoId}`);
                        player.playVideo();
                        player.mute();
                    } else {
                        console.log(`Stopping video ${videoId}`);
                        player.stopVideo();
                        player.unMute();
                    }
                } catch (error) {
                    console.error(`Error controlling player for video ${videoId}:`, error);
                }
            });
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
            if (this.autoplayEnabled) {
                event.target.playVideo();
                event.target.mute();
            }
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
