function updateTimeAgo() {
	const timeElement = document.getElementById('last-updated');
	const datetimeString = timeElement.getAttribute('datetime');
	const datetime = new Date(datetimeString);
	const now = new Date();
	const diffInSeconds = Math.floor((now - datetime) / 1000);

	let timeAgoText;

	if (diffInSeconds < 60) {
		timeAgoText = `${diffInSeconds} second${diffInSeconds !== 1 ? 's' : ''} ago`;
	} else {
		const minutes = Math.floor(diffInSeconds / 60);
		const hours = Math.floor(minutes / 60);
		const days = Math.floor(hours / 24);
		
		if (days > 0) {
			timeAgoText = `${days} day${days !== 1 ? 's' : ''}${hours % 24 > 0 ? `, ${hours % 24} hour${hours % 24 !== 1 ? 's' : ''}` : ''} ago`;
		} else if (hours > 0) {
			timeAgoText = `${hours} hour${hours !== 1 ? 's' : ''}${minutes % 60 > 0 ? `, ${minutes % 60} minute${minutes % 60 !== 1 ? 's' : ''}` : ''} ago`;
		} else {
			timeAgoText = `${minutes} minute${minutes !== 1 ? 's' : ''} ago`;
		}
	}

	timeElement.textContent = timeAgoText;
}

function updateExpiredLinks() {
	const times = document.querySelectorAll('time.endtime');

	times.forEach(function(time) {
		const endTime = new Date(time.getAttribute('datetime'));
		const currentTime = new Date();

		if (currentTime > endTime) {
			const link = time.previousElementSibling;  // The <a> tag before the <time> tag
			link.style.textDecoration = 'line-through';  // Strike out the link
		}
	});
}

// Call the function when the DOM is fully loaded
document.addEventListener('DOMContentLoaded', function() {
	updateTimeAgo();
	setInterval(updateTimeAgo, 60000);  // Update every 60 seconds
});
document.addEventListener('DOMContentLoaded', function() {
	updateExpiredLinks();
	setInterval(updateExpiredLinks, 60000 * 5);  // Update every 5 minues
})
