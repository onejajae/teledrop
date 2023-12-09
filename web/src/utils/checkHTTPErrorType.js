function is409Conflict(error) {
	return error.response.status === 409;
}

export { is409Conflict };
