import { useState, useCallback } from "react";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

/**
 * Owns the call to POST /api/v1/generate.
 *
 * `status` is a single enum (idle | loading | success | error) rather than
 * separate booleans, so the UI can never end up in a contradictory state
 * (e.g. isLoading && hasError both true) — see design-system.md Section 5.
 */
export function useGenerate() {
  const [status, setStatus] = useState("idle");
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);

  const generate = useCallback(async (file, language) => {
    setStatus("loading");
    setError(null);

    const formData = new FormData();
    formData.append("file", file);
    formData.append("language", language);

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/generate`, {
        method: "POST",
        body: formData,
      });

      const body = await response.json();

      if (!response.ok) {
        // Backend error shape is { error: { code, message } } — see
        // api-spec.md Section 3. message is already written to be
        // user-safe (PRD FR-7.1), so we surface it directly.
        const message =
          body?.error?.message ??
          "Something went wrong generating your notes. Please try again.";
        setError(message);
        setStatus("error");
        return;
      }

      setResults(body);
      setStatus("success");
    } catch {
      // Network failure, backend unreachable, etc. — never let this reach
      // the user as an unhandled exception or blank screen.
      setError("Could not reach the server. Check your connection and try again.");
      setStatus("error");
    }
  }, []);

  const reset = useCallback(() => {
    setStatus("idle");
    setResults(null);
    setError(null);
  }, []);

  return { generate, reset, status, results, error };
}
