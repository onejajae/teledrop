function isImage(mime) {
	return mime.startsWith('image/');
}

function isVideo(mime) {
	return mime.startsWith('video/');
}

function isPDF(mime) {
	return mime.startsWith('application/pdf');
}

export { isImage, isVideo, isPDF };
