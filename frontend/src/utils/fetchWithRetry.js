/**
 * Fetches a resource with automatic retry on network failures.
 * Uses exponential backoff: 2s, 4s, 8s, 16s between retries.
 *
 * @param {string|Request} input - The URL or Request object to fetch
 * @param {RequestInit} init - Fetch options (method, headers, body, etc.)
 * @param {number} maxRetries - Maximum number of retry attempts (default: 4)
 * @returns {Promise<Response>} The fetch response
 * @throws {Error} If all retry attempts fail
 */
export async function fetchWithRetry(input, init = {}, maxRetries = 4) {
  let lastError;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      const response = await fetch(input, init);

      // Don't retry on HTTP errors (4xx, 5xx) - only network failures
      // If we get a response, even if it's an error status, return it
      return response;

    } catch (error) {
      lastError = error;

      // Check if this is a network error (TypeError with "Load failed" or "network" in message)
      const isNetworkError =
        error instanceof TypeError &&
        (error.message.includes('Load failed') ||
         error.message.includes('network') ||
         error.message.includes('Failed to fetch'));

      // If it's not a network error, or we've exhausted retries, throw immediately
      if (!isNetworkError || attempt >= maxRetries) {
        console.error(`Fetch failed after ${attempt + 1} attempts:`, error);
        throw error;
      }

      // Calculate exponential backoff delay: 2s, 4s, 8s, 16s
      const delay = Math.pow(2, attempt + 1) * 1000;

      console.warn(
        `Network error on attempt ${attempt + 1}/${maxRetries + 1}. ` +
        `Retrying in ${delay / 1000}s...`,
        error.message
      );

      // Wait before retrying
      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }

  // This should never be reached, but just in case
  throw lastError;
}

/**
 * Helper function to make a GET request with retry logic
 * @param {string} url - The URL to fetch
 * @param {RequestInit} options - Additional fetch options
 * @returns {Promise<any>} Parsed JSON response
 */
export async function fetchJsonWithRetry(url, options = {}) {
  const response = await fetchWithRetry(url, options);

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return await response.json();
}
