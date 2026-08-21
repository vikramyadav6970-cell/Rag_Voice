/**
 * Centralized API Client — Voice-Enabled Indic RAG Backend Connector.
 * Follows coding_conventions.md: single frontend module, standard error handling, no scattered fetch calls.
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * Submit voice audio recording to /api/ask for full RAG pipeline execution.
 * 
 * @param {Blob} audioBlob - Recorded audio blob (WAV/WebM)
 * @param {string} [languageHint] - Language code (e.g. 'hin', 'tam', 'hi-IN')
 * @param {string} [strategy] - Chunking strategy filter ('passage_native', 'fixed_size', 'semantic', 'hierarchical_child')
 * @returns {Promise<Object>} Response object: { transcript, query, answer, sources, timings_ms, guardrail_flags, detected_language, success, errors }
 */
export async function askQuestion(audioBlob, languageHint = 'hin', strategy = 'passage_native') {
  const formData = new FormData();
  formData.append('file', audioBlob, 'recording.wav');
  if (languageHint) {
    formData.append('language_hint', languageHint);
  }
  if (strategy) {
    formData.append('strategy', strategy);
  }

  try {
    const response = await fetch(`${API_BASE_URL}/api/ask`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      let errorDetail = `Server returned status ${response.status}`;
      try {
        const errJson = await response.json();
        errorDetail = errJson.detail || errorDetail;
      } catch {
        // Fall back to status text
      }
      throw new Error(errorDetail);
    }

    const data = await response.json();
    return data;
  } catch (err) {
    console.error('API askQuestion error:', err);
    throw err;
  }
}

/**
 * Submit natural language text query to /api/ask/text.
 * 
 * @param {string} query - Question text
 * @param {string} [language] - Language filter ('hin', 'tam', 'en')
 * @param {string} [strategy] - Chunking strategy override
 * @param {number} [topK=4] - Number of evidence passages
 * @returns {Promise<Object>}
 */
export async function askTextQuestion(query, language = 'hin', strategy = 'passage_native', topK = 4) {
  try {
    const response = await fetch(`${API_BASE_URL}/api/ask/text`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        query,
        language,
        strategy,
        top_k: topK,
      }),
    });

    if (!response.ok) {
      const errJson = await response.json().catch(() => ({}));
      throw new Error(errJson.detail || `Server returned status ${response.status}`);
    }

    return await response.json();
  } catch (err) {
    console.error('API askTextQuestion error:', err);
    throw err;
  }
}

/**
 * Check backend operational health diagnostic.
 * 
 * @returns {Promise<Object>} { status: 'healthy', service: 'voice-rag-backend', ... }
 */
export async function checkHealth() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/health`);
    if (!response.ok) {
      throw new Error(`Health check failed with status ${response.status}`);
    }
    return await response.json();
  } catch (err) {
    console.error('API checkHealth error:', err);
    throw err;
  }
}
