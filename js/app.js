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
    card.className = 'stream-card bg-white rounded-lg shadow-md overflow-hidden';

    const content = `
        <div class="aspect-w-16 aspect-h-9">
            ${isLive ?
            `<iframe 
                    src="https://www.youtube.com/embed/${item.videoId}" 
                    frameborder="0" 
                    allow="accelerometer; clipboard-write; encrypted-media; gyroscope; picture-in-picture" 
                    allowfullscreen
                    class="w-full h-full">
                </iframe>` :
            `<img src="https://img.youtube.com/vi/${item.videoId}/maxresdefault.jpg" alt="${item.title}" class="w-full h-full object-cover">`
        }
        </div>
        <div class="p-4">
            <h3 class="text-lg font-semibold text-gray-900 mb-2">${item.title}</h3>
            <p class="text-sm text-gray-600">${item.channelName}</p>
            ${isLive ?
            '<span class="inline-block px-2 py-1 text-xs font-semibold text-red-600 bg-red-100 rounded-full mt-2">LIVE</span>' :
            `<p class="text-sm text-gray-600 mt-2">Scheduled: ${new Date(item.scheduledStartTime).toLocaleString()}</p>`
        }
        </div>
    `;

    card.innerHTML = content;
    return card;
}

// Load data when the page loads
document.addEventListener('DOMContentLoaded', loadStreamData);

// Refresh data every 5 minutes
setInterval(loadStreamData, 5 * 60 * 1000); 