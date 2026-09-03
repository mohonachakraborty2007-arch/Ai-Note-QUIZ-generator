import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import QuizTab from "../QuizTab";

const mcqs = [
  {
    question: "What does the first law of thermodynamics state?",
    options: ["Energy is conserved", "Entropy decreases", "Mass increases", "Time reverses"],
    correct_answer: "Energy is conserved",
    explanation: "Energy cannot be created or destroyed.",
  },
  {
    question: "What is entropy?",
    options: ["A measure of disorder", "A type of energy", "A force", "A particle"],
    correct_answer: "A measure of disorder",
    explanation: "Entropy measures the disorder of a system.",
  },
];

describe("QuizTab", () => {
  it("increments score on a correct answer", () => {
    render(<QuizTab mcqs={mcqs} />);
    fireEvent.click(screen.getByText("Energy is conserved"));
    expect(screen.getByText("Score: 1/2")).toBeInTheDocument();
  });

  it("does not increment score on an incorrect answer", () => {
    render(<QuizTab mcqs={mcqs} />);
    fireEvent.click(screen.getByText("Entropy decreases"));
    expect(screen.getByText("Score: 0/2")).toBeInTheDocument();
  });

  it("ignores a second click after the question is already answered", () => {
    // Regression test for the exact bug class called out in testing.md
    // Section 2: an off-by-one in scoring from a double-count is invisible
    // in casual manual testing but easy to introduce in a refactor.
    render(<QuizTab mcqs={mcqs} />);
    fireEvent.click(screen.getByText("Energy is conserved")); // correct
    fireEvent.click(screen.getByText("Entropy decreases")); // should be a no-op
    expect(screen.getByText("Score: 1/2")).toBeInTheDocument();
  });

  it("advances to the next question and resets answered state", () => {
    render(<QuizTab mcqs={mcqs} />);
    fireEvent.click(screen.getByText("Energy is conserved"));
    fireEvent.click(screen.getByText("Next Question"));
    expect(screen.getByText("What is entropy?")).toBeInTheDocument();
    expect(screen.getByText("Question 2 of 2")).toBeInTheDocument();
  });

  it("shows the final score screen after the last question", () => {
    render(<QuizTab mcqs={mcqs} />);
    fireEvent.click(screen.getByText("Energy is conserved")); // correct
    fireEvent.click(screen.getByText("Next Question"));
    fireEvent.click(screen.getByText("A measure of disorder")); // correct
    fireEvent.click(screen.getByText("See Results"));
    expect(screen.getByText("You got 2/2")).toBeInTheDocument();
  });

  it("resets state on Retake Quiz", () => {
    render(<QuizTab mcqs={mcqs} />);
    fireEvent.click(screen.getByText("Energy is conserved"));
    fireEvent.click(screen.getByText("Next Question"));
    fireEvent.click(screen.getByText("A measure of disorder"));
    fireEvent.click(screen.getByText("See Results"));
    fireEvent.click(screen.getByText("Retake Quiz"));
    expect(screen.getByText("Question 1 of 2")).toBeInTheDocument();
    expect(screen.getByText("Score: 0/2")).toBeInTheDocument();
  });
});
