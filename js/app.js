// Stream data loading
async function loadStreamData() {
    try {
        const response = await fetch('data/streams.json');
        const data = await response.json();
        updateStreams(data);
    } catch (error) {
        console.error('Error loading stream data:', error);
    }
}

function updateStreams(data) {
    const liveStreamsContainer = document.getElementById('live-streams');
    const upcomingMatchesContainer = document.getElementById('upcoming-matches');

    // Clear existing content
    liveStreamsContainer.innerHTML = '';
    upcomingMatchesContainer.innerHTML = '';

    // Update live streams
    if (data.liveStreams && data.liveStreams.length > 0) {
        data.liveStreams.forEach(stream => {
            const streamCard = createStreamCard(stream, true);
            liveStreamsContainer.appendChild(streamCard);
        });
    } else {
        liveStreamsContainer.innerHTML = '<p class="text-gray-600">No live streams at the moment.</p>';
    }

    // Update upcoming matches
    if (data.upcomingMatches && data.upcomingMatches.length > 0) {
        data.upcomingMatches.forEach(match => {
            const matchCard = createStreamCard(match, false);
            upcomingMatchesContainer.appendChild(matchCard);
        });
    } else {
        upcomingMatchesContainer.innerHTML = '<p class="text-gray-600">No upcoming matches scheduled.</p>';
    }
}

function createStreamCard(item, isLive) {
    const card = document.createElement('div');
    card.className = 'stream-card bg-white rounded-lg shadow-md overflow-hidden hover:shadow-lg transition-shadow duration-200';

    const videoContainer = document.createElement('div');
    videoContainer.className = 'relative aspect-w-16 aspect-h-9';

    if (isLive) {
        // Create a container for the video
        const videoWrapper = document.createElement('div');
        videoWrapper.className = 'absolute inset-0 w-full h-full';

        // Create the iframe
        const iframe = document.createElement('iframe');
        iframe.className = 'absolute inset-0 w-full h-full';
        iframe.src = `https://www.youtube.com/embed/${item.videoId}?autoplay=1&mute=1`;
        iframe.allow = 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture';
        iframe.allowFullscreen = true;

        // Add error handling for non-embeddable videos
        iframe.onerror = () => {
            // Replace iframe with thumbnail and play button
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

            // Add click handler to open video in new tab
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
        time.textContent = 'LIVE NOW';
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

// Load data when the page loads
document.addEventListener('DOMContentLoaded', loadStreamData);

// Refresh data every 5 minutes
setInterval(loadStreamData, 5 * 60 * 1000); 