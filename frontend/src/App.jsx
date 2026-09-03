import { useState } from "react";
import UploadForm from "./components/UploadForm.jsx";
import QuizTab from "./components/QuizTab.jsx";

function App() {
  const [result, setResult] = useState(null);

  return (
    <div style={{ maxWidth: "800px", margin: "40px auto", padding: "0 20px" }}>
      <h1>AI Note & Quiz Generator</h1>
      {!result ? (
        <UploadForm onGenerated={setResult} />
      ) : (
        <div>
          <h2>Summary</h2>
          <p>{result.summary}</p>
          <h2>Key Points</h2>
          <ul>
            {result.key_points?.map((point, i) => (
              <li key={i}>{point}</li>
            ))}
          </ul>
          <QuizTab mcqs={result.mcqs} />
          <button onClick={() => setResult(null)} style={{ marginTop: "20px" }}>
            Generate Another
          </button>
        </div>
      )}
    </div>
  );
}

export default App;