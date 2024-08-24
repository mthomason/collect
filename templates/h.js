function updateTimeAgo() {
	const timeElement = document.getElementById('last-updated');
	const datetimeString = timeElement.getAttribute('datetime');
	const datetime = new Date(datetimeString);
	const now = new Date();
	const diffInSeconds = Math.floor((now - datetime) / 1000);

	let timeAgoText;

	if (diffInSeconds < 60) {
		timeAgoText = `${diffInSeconds} seconds ago`;
	} else if (diffInSeconds < 3600) {
		const minutes = Math.floor(diffInSeconds / 60);
		timeAgoText = `${minutes} minute${minutes !== 1 ? 's' : ''} ago`;
	} else if (diffInSeconds < 86400) {
		const hours = Math.floor(diffInSeconds / 3600);
		timeAgoText = `${hours} hour${hours !== 1 ? 's' : ''} ago`;
	} else {
		const days = Math.floor(diffInSeconds / 86400);
		timeAgoText = `${days} day${days !== 1 ? 's' : ''} ago`;
	}

	timeElement.textContent = timeAgoText;
}

// Call the function when the DOM is fully loaded
document.addEventListener('DOMContentLoaded', function() {
	updateTimeAgo();
	setInterval(updateTimeAgo, 60000);  // Update every 60 seconds
});
