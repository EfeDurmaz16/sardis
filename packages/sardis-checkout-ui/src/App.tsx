import { Routes, Route } from "react-router-dom";
import CheckoutPage from "./pages/CheckoutPage";
import DemoPage from "./pages/DemoPage";

function RedirectToMain() {
  window.location.href = "https://sardis.sh";
  return null;
}

export default function App() {
  return (
    <Routes>
      <Route path="/demo" element={<DemoPage />} />
      <Route path="/:sessionId" element={<CheckoutPage />} />
      <Route path="*" element={<RedirectToMain />} />
    </Routes>
  );
}
