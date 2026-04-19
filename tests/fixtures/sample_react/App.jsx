// Sample React component with intentional security issues
import React, { useState } from "react";

function App() {
  const [userInput, setUserInput] = useState("");

  // XSS: dangerouslySetInnerHTML with unsanitised user input
  const renderHtml = () => (
    <div dangerouslySetInnerHTML={{ __html: userInput }} />
  );

  // Unsafe eval
  const calculate = (expr) => {
    return eval(expr);  // eslint-disable-line no-eval
  };

  return (
    <div>
      <input
        value={userInput}
        onChange={(e) => setUserInput(e.target.value)}
      />
      {renderHtml()}
      <button onClick={() => calculate("1+1")}>Calc</button>
    </div>
  );
}

export default App;
