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
        autoplayEnabled: getCookie('autoplayEnabled') === 'true',
        iframes: new Map(),

        init() {
            this.loadStreamData();
            setInterval(() => this.loadStreamData(), 5 * 60 * 1000);
        },

        toggleAutoplay() {
            setCookie('autoplayEnabled', this.autoplayEnabled, 365);
            this.updateAllIframes();
        },

        updateAllIframes() {
            this.iframes.forEach((iframe, videoId) => {
                // Store the current time of the video
                const currentTime = iframe.contentWindow?.getCurrentTime?.() || 0;

                // Create new iframe with updated parameters
                const newIframe = document.createElement('iframe');
                newIframe.className = iframe.className;
                newIframe.allow = iframe.allow;
                newIframe.allowFullscreen = iframe.allowFullscreen;

                // Set the new source with appropriate parameters
                const params = new URLSearchParams();
                if (this.autoplayEnabled) {
                    params.append('autoplay', '1');
                    params.append('mute', '1');
                }
                if (currentTime > 0) {
                    params.append('start', Math.floor(currentTime));
                }
                newIframe.src = `https://www.youtube.com/embed/${videoId}?${params.toString()}&origin=${encodeURIComponent(window.location.origin)}&enablejsapi=1`;

                // Replace the old iframe with the new one
                iframe.parentNode.replaceChild(newIframe, iframe);

                // Update the reference in our map
                this.iframes.set(videoId, newIframe);
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
            const liveStreamsContainer = document.getElementById('live-streams');
            const upcomingMatchesContainer = document.getElementById('upcoming-matches');

            // Clear existing content
            liveStreamsContainer.innerHTML = '';
            upcomingMatchesContainer.innerHTML = '';
            this.iframes.clear();

            // Update live streams
            if (data.liveStreams && data.liveStreams.length > 0) {
                data.liveStreams.forEach(stream => {
                    const streamCard = this.createStreamCard(stream, true);
                    liveStreamsContainer.appendChild(streamCard);
                });
            } else {
                liveStreamsContainer.innerHTML = '<p class="text-gray-600">No live streams at the moment.</p>';
            }

            // Update upcoming matches
            if (data.upcomingMatches && data.upcomingMatches.length > 0) {
                data.upcomingMatches.forEach(match => {
                    const matchCard = this.createStreamCard(match, false);
                    upcomingMatchesContainer.appendChild(matchCard);
                });
            } else {
                upcomingMatchesContainer.innerHTML = '<p class="text-gray-600">No upcoming matches scheduled.</p>';
            }
        },

        createStreamCard(item, isLive) {
            const card = document.createElement('div');
            card.className = 'stream-card bg-white rounded-lg shadow-md overflow-hidden';

            const videoContainer = document.createElement('div');
            videoContainer.className = 'relative aspect-w-16 aspect-h-9';

            if (isLive) {
                const videoWrapper = document.createElement('div');
                videoWrapper.className = 'absolute inset-0 w-full h-full';

                const iframe = document.createElement('iframe');
                iframe.className = 'absolute inset-0 w-full h-full';
                iframe.src = `https://www.youtube.com/embed/${item.videoId}${this.autoplayEnabled ? '?autoplay=1&mute=1' : ''}&origin=${encodeURIComponent(window.location.origin)}&enablejsapi=1`;
                iframe.allow = 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture';
                iframe.allowFullscreen = true;

                // Store iframe reference for autoplay toggling
                this.iframes.set(item.videoId, iframe);

                // Add error handling for non-embeddable videos
                iframe.onerror = () => {
                    const thumbnail = document.createElement('img');
                    thumbnail.className = 'absolute inset-0 w-full h-full object-cover';
                    thumbnail.src = `https://img.youtube.com/vi/${item.videoId}/maxresdefault.jpg`;
                    thumbnail.alt = item.title;

                    const playButton = document.createElement('div');
                    playButton.className = 'absolute inset-0 flex items-center justify-center bg-black bg-opacity-50';
                    playButton.innerHTML = `
                        <div class="text-white text-center">
                            <svg class="w-16 h-16 mx-auto mb-2" fill="currentColor" viewBox="0 0 20 20">
                                <path d="M6.3 2.841A1.5 1.5 0 004 4.11V15.89a1.5 1.5 0 002.3 1.269l9.344-5.89a1.5 1.5 0 000-2.538L6.3 2.84z"/>
                            </svg>
                            <p class="text-sm">Watch on YouTube</p>
                        </div>
                    `;

                    playButton.onclick = () => {
                        window.open(`https://www.youtube.com/watch?v=${item.videoId}`, '_blank');
                    };

                    videoWrapper.innerHTML = '';
                    videoWrapper.appendChild(thumbnail);
                    videoWrapper.appendChild(playButton);
                };

                videoWrapper.appendChild(iframe);
                videoContainer.appendChild(videoWrapper);
            } else {
                const thumbnail = document.createElement('img');
                thumbnail.className = 'absolute inset-0 w-full h-full object-cover';
                thumbnail.src = `https://img.youtube.com/vi/${item.videoId}/maxresdefault.jpg`;
                thumbnail.alt = item.title;
                videoContainer.appendChild(thumbnail);
            }

            const content = document.createElement('div');
            content.className = 'p-4';

            const title = document.createElement('h3');
            title.className = 'text-lg font-semibold text-gray-900 mb-2';
            title.textContent = item.title;

            const channel = document.createElement('p');
            channel.className = 'text-sm text-gray-600';
            channel.textContent = item.channelName;

            const time = document.createElement('p');
            time.className = 'text-sm text-gray-500 mt-2';
            if (isLive) {
                time.innerHTML = '<span class="inline-block px-2 py-1 text-xs font-semibold text-red-600 bg-red-100 rounded-full">LIVE</span>';
            } else {
                const startTime = new Date(item.scheduledStartTime);
                const now = new Date();
                const diff = startTime - now;
                const hours = Math.floor(diff / (1000 * 60 * 60));
                const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
                time.textContent = `Starts in ${hours}h ${minutes}m`;
            }

            content.appendChild(title);
            content.appendChild(channel);
            content.appendChild(time);

            card.appendChild(videoContainer);
            card.appendChild(content);

            return card;
        }
    }
}

// Initialize when the page loads
document.addEventListener('DOMContentLoaded', () => {
    streamApp().init();
}); 