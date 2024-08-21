
document.addEventListener("DOMContentLoaded", function() {
	const now = new Date();

	document.querySelectorAll('time.auction-end-time').forEach(timeTag => {
		const endTime = new Date(timeTag.getAttribute('datetime'));
		const link = timeTag.closest('a');

		if (endTime <= now) {
			link.innerHTML = `<s>${link.textContent}</s>`;
			link.classList.add('ended');
		} else if ((endTime - now) <= 3600000) { // Less than an hour
			link.innerHTML = `⏰ ${link.textContent}`;
			link.classList.add('ending');
		}
	});
});
