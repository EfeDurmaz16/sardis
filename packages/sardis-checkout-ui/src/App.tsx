import { Routes, Route } from "react-router-dom";
import CheckoutPage from "./pages/CheckoutPage";

export default function App() {
  return (
    <Routes>
      <Route path="/:sessionId" element={<CheckoutPage />} />
    </Routes>
  );
}
