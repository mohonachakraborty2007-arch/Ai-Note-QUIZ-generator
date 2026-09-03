import { useRef, useState } from "react";
import { useGenerate } from "../hooks/useGenerate";

const LANGUAGES = [
  { code: "en", label: "English" },
  { code: "hi", label: "हिन्दी" },
  { code: "bn", label: "বাংলা" },
];

const MAX_FILE_SIZE_BYTES = 15 * 1024 * 1024; // FR-1.3

/**
 * Upload screen (design-system.md Section 4). Renders when no results exist
 * yet; ResultsTabs takes over once `onGenerated` fires.
 */
export default function UploadForm({ onGenerated }) {
  const [file, setFile] = useState(null);
  const [language, setLanguage] = useState("en");
  const [isDragActive, setIsDragActive] = useState(false);
  const [localError, setLocalError] = useState(null);
  const fileInputRef = useRef(null);

  const { generate, status, results, error } = useGenerate();

  // Success is handled via an effect-free pattern: once results land, hand
  // them up to the parent immediately.
  if (status === "success" && results) {
    onGenerated(results, file?.name, language);
  }

  function validateAndSetFile(candidate) {
    setLocalError(null);

    if (!candidate) return;

    if (candidate.type !== "application/pdf") {
      setLocalError("Only PDF files are accepted.");
      return;
    }
    if (candidate.size > MAX_FILE_SIZE_BYTES) {
      setLocalError("File exceeds the 15MB limit.");
      return;
    }
    setFile(candidate);
  }

  function handleDrop(e) {
    e.preventDefault();
    setIsDragActive(false);
    validateAndSetFile(e.dataTransfer.files?.[0]);
  }

  function handleBrowseClick() {
    fileInputRef.current?.click();
  }

  function handleSubmit(e) {
    e.preventDefault();
    if (!file) return;
    generate(file, language);
  }

  const isLoading = status === "loading";
  const displayError = localError ?? error;

  return (
    <div className="max-w-xl mx-auto px-4 py-10">
      <h1 className="text-2xl font-semibold text-stone-900 mb-1">
        AI Lecture Notes &amp; Quiz Generator
      </h1>
      <p className="text-sm text-stone-600 mb-6">
        Upload a lecture PDF and get a summary, key points, and a self-test
        quiz in under a minute.
      </p>

      {displayError && (
        <div
          role="alert"
          aria-live="polite"
          className="mb-4 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800"
        >
          {displayError}
        </div>
      )}

      <form onSubmit={handleSubmit}>
        {/* FileDropzone */}
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setIsDragActive(true);
          }}
          onDragLeave={() => setIsDragActive(false)}
          onDrop={handleDrop}
          onClick={handleBrowseClick}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") handleBrowseClick();
          }}
          className={`cursor-pointer rounded-lg border-2 border-dashed px-6 py-10 text-center transition-colors ${
            isDragActive
              ? "border-indigo-500 bg-indigo-50"
              : "border-stone-300 bg-white"
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept="application/pdf"
            className="hidden"
            onChange={(e) => validateAndSetFile(e.target.files?.[0])}
          />
          {file ? (
            <div className="flex items-center justify-center gap-2 text-stone-800">
              <span className="text-sm font-medium">{file.name}</span>
              <span className="text-xs text-stone-500">
                ({Math.round(file.size / 1024)} KB)
              </span>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  setFile(null);
                }}
                aria-label="Remove selected file"
                className="ml-2 text-stone-400 hover:text-stone-700"
              >
                ×
              </button>
            </div>
          ) : (
            <p className="text-sm text-stone-600">
              Drop your lecture PDF here, or click to browse.
            </p>
          )}
        </div>

        {/* LanguageSelector — segmented control, not a dropdown (design-system.md Sec 3) */}
        <div
          role="radiogroup"
          aria-label="Output language"
          className="mt-6 flex gap-2"
        >
          {LANGUAGES.map((lang) => (
            <button
              key={lang.code}
              type="button"
              role="radio"
              aria-checked={language === lang.code}
              onClick={() => setLanguage(lang.code)}
              className={`flex-1 min-h-[44px] rounded-md border px-3 py-2 text-base transition-colors ${
                language === lang.code
                  ? "border-indigo-600 bg-indigo-600 text-white"
                  : "border-stone-300 bg-white text-stone-700 hover:border-indigo-300"
              }`}
            >
              {lang.label}
            </button>
          ))}
        </div>

        {/* Primary action */}
        <button
          type="submit"
          disabled={!file || isLoading}
          className="mt-6 w-full rounded-md bg-indigo-600 px-4 py-3 text-base font-semibold text-white transition-colors disabled:cursor-not-allowed disabled:bg-stone-300"
        >
          {isLoading ? "Generating…" : "Generate Notes & Quiz"}
        </button>

        {isLoading && (
          <p
            aria-live="polite"
            className="mt-3 text-center text-sm text-stone-500"
          >
            Reading your PDF and generating your revision notes — this can
            take up to 30 seconds.
          </p>
        )}
      </form>
    </div>
  );
}
