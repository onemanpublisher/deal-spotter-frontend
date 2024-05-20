// Function to format time difference with timezone
function formatTimeDifferenceWithTimezone(timestamp) {
    const commentTime = new Date(timestamp);
    const options = { timeZoneName: 'short' };
    const formattedTimestamp = new Intl.DateTimeFormat('de-DE', options).format(commentTime);
    const currentTime = new Date();
    const timeDifference = currentTime - commentTime;

    const seconds = Math.floor(timeDifference / 1000);
    if (seconds < 60) {
        return `vor ${seconds} Sekunde${seconds === 1 ? '' : 'n'}`;
    } else if (seconds < 3600) {
        const minutes = Math.floor(seconds / 60);
        return `vor ${minutes} Minute${minutes === 1 ? '' : 'n'}`;
    } else if (seconds < 86400) {
        const hours = Math.floor(seconds / 3600);
        return `vor ${hours} Stunde${hours === 1 ? '' : 'n'}`;
    } else {
        const days = Math.floor(seconds / 86400);
        return `vor ${days} Tag${days === 1 ? '' : 'en'}`;
    }
}

// Function to update timestamps when the page loads
window.onload = function () {
    // Get all elements with the class "comment-timestamp"
    const commentTimestamps = document.querySelectorAll(".comment-timestamp");

    // Iterate through each comment timestamp and update the content
    commentTimestamps.forEach(timestampElement => {
        const timestamp = timestampElement.getAttribute("data-timestamp");
        const formattedTime = formatTimeDifferenceWithTimezone(timestamp);
        timestampElement.textContent = formattedTime; // Update the content
    });
};