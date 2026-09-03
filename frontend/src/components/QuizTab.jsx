import { useRef, useState } from "react";

/**
 * Quiz tab — the most stateful piece of the UI (design-system.md Section 8).
 * All state is local (useState), per ADR-5 in architecture.md: quiz progress
 * and score live only in this component and reset on reload/retake, which
 * is explicitly allowed by PRD FR-5.5.
 *
 * mcqs: [{ question, options, correct_answer, explanation }]
 */
export default function QuizTab({ mcqs }) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [selectedOption, setSelectedOption] = useState(null);
  const [score, setScore] = useState(0);
  const [isFinished, setIsFinished] = useState(false);
  const questionHeadingRef = useRef(null);

  const currentQuestion = mcqs[currentIndex];
  const hasAnswered = selectedOption !== null;

  function handleSelectOption(option) {
    if (hasAnswered) return; // FR: disabled after answering
    setSelectedOption(option);
    if (option === currentQuestion.correct_answer) {
      setScore((s) => s + 1); // FR-5.3: running score
    }
  }

  function handleNext() {
    const isLastQuestion = currentIndex === mcqs.length - 1;
    if (isLastQuestion) {
      setIsFinished(true); // FR-5.4: final score summary
      return;
    }
    setCurrentIndex((i) => i + 1);
    setSelectedOption(null);
    // Move focus to the next question's heading — screen reader users land
    // on new content rather than staying anchored (design-system.md Sec 6).
    questionHeadingRef.current?.focus();
  }

  function handleRetake() {
    setCurrentIndex(0);
    setSelectedOption(null);
    setScore(0);
    setIsFinished(false);
  }

  if (mcqs.length === 0) {
    return (
      <p className="text-sm text-stone-600">
        No quiz questions were generated for this lecture.
      </p>
    );
  }

  if (isFinished) {
    return (
      <div className="text-center py-10">
        <p className="text-3xl font-semibold text-stone-900">
          You got {score}/{mcqs.length}
        </p>
        <p className="mt-2 text-stone-600">Nice work.</p>
        <div className="mt-6 flex justify-center gap-3">
          <button
            onClick={handleRetake}
            className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-semibold text-white"
          >
            Retake Quiz
          </button>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-4 flex items-center justify-between text-sm text-stone-500">
        <span>
          Question {currentIndex + 1} of {mcqs.length}
        </span>
        <span aria-live="polite">Score: {score}/{mcqs.length}</span>
      </div>

      <h2
        ref={questionHeadingRef}
        tabIndex={-1}
        className="text-lg font-semibold text-stone-900 mb-4 outline-none"
      >
        {currentQuestion.question}
      </h2>

      <div className="flex flex-col gap-3">
        {currentQuestion.options.map((option) => {
          const isSelected = selectedOption === option;
          const isCorrectOption = option === currentQuestion.correct_answer;

          // Never color-alone (design-system.md Sec 6): icon + text pair
          // with color for both correct and incorrect states.
          let stateClasses =
            "border-stone-300 bg-white text-stone-800 hover:border-indigo-300";
          let icon = null;

          if (hasAnswered && isCorrectOption) {
            stateClasses = "border-green-600 bg-green-50 text-green-800";
            icon = "✓";
          } else if (hasAnswered && isSelected && !isCorrectOption) {
            stateClasses = "border-red-600 bg-red-50 text-red-800";
            icon = "×";
          }

          return (
            <button
              key={option}
              type="button"
              disabled={hasAnswered}
              onClick={() => handleSelectOption(option)}
              className={`flex items-center justify-between rounded-md border px-4 py-3 text-left text-base transition-colors disabled:cursor-default ${stateClasses}`}
            >
              <span>{option}</span>
              {icon && <span aria-hidden="true" className="font-semibold">{icon}</span>}
            </button>
          );
        })}
      </div>

      {hasAnswered && (
        <div className="mt-4 rounded-md bg-stone-50 border border-stone-200 p-4">
          <p className="text-sm text-stone-700">{currentQuestion.explanation}</p>
          <button
            onClick={handleNext}
            className="mt-4 rounded-md bg-indigo-600 px-4 py-2 text-sm font-semibold text-white"
          >
            {currentIndex === mcqs.length - 1 ? "See Results" : "Next Question"}
          </button>
        </div>
      )}
    </div>
  );
}
