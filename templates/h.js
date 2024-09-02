document.addEventListener('DOMContentLoaded', function() {
	// Update intervals
	const UPDATE_INTERVAL_TIME_AGO = 60000;  // 60 seconds
	const UPDATE_INTERVAL_EXPIRED_LINKS = 60000 * 5;  // 5 minutes

	// Helper function to pluralize time units
	const pluralize = (value, unit) => `${value} ${unit}${value !== 1 ? 's' : ''}`;

	// Update the "time ago" text
	function updateTimeAgo() {
		const timeElement = document.getElementById('last-updated');
		const datetimeString = timeElement.getAttribute('datetime');
		const datetime = new Date(datetimeString);
		const now = new Date();
		const diffInSeconds = Math.floor((now - datetime) / 1000);

		let timeAgoText;

		if (diffInSeconds < 60) {
			timeAgoText = pluralize(diffInSeconds, 'second') + ' ago';
		} else {
			const minutes = Math.floor(diffInSeconds / 60);
			const hours = Math.floor(minutes / 60);
			const days = Math.floor(hours / 24);
			
			if (days > 0) {
				timeAgoText = pluralize(days, 'day') + (hours % 24 > 0 ? `, ${pluralize(hours % 24, 'hour')}` : '') + ' ago';
			} else if (hours > 0) {
				timeAgoText = pluralize(hours, 'hour') + (minutes % 60 > 0 ? `, ${pluralize(minutes % 60, 'minute')}` : '') + ' ago';
			} else {
				timeAgoText = pluralize(minutes, 'minute') + ' ago';
			}
		}

		timeElement.textContent = timeAgoText;
	}

	// Update expired links
	function updateExpiredLinks() {
		const times = document.querySelectorAll('time.endtime');
		const currentTime = new Date();

		times.forEach(time => {
			const endTime = new Date(time.getAttribute('datetime'));

			if (currentTime > endTime) {
				const link = time.previousElementSibling;  // The <a> tag before the <time> tag
				link.style.textDecoration = 'line-through';  // Strike out the link
			}
		});
	}

	// Initial calls
	updateTimeAgo();
	updateExpiredLinks();

	// Set intervals
	setInterval(updateTimeAgo, UPDATE_INTERVAL_TIME_AGO);
	setInterval(updateExpiredLinks, UPDATE_INTERVAL_EXPIRED_LINKS);
});
