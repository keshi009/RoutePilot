import { BrowserRouter, Route, Routes } from "react-router-dom";
import OrderListPage from "./pages/OrderListPage";
import PlanningPage from "./pages/PlanningPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<OrderListPage />} />
        <Route path="/planning" element={<PlanningPage />} />
      </Routes>
    </BrowserRouter>
  );
}
