import { Route, Routes } from "react-router-dom";
import { MainLayout } from "@/layouts/MainLayout";
import { ProtectedRoute } from "@/routes/ProtectedRoute";
import Home from "@/pages/Home";
import Explore from "@/pages/Explore";
import PropertyDetails from "@/pages/PropertyDetails";
import Assistant from "@/pages/Assistant";
import Compare from "@/pages/Compare";
import Favorites from "@/pages/Favorites";
import Dashboard from "@/pages/Dashboard";
import { Login, Register } from "@/pages/AuthPages";
import Profile from "@/pages/Profile";
import Contact from "@/pages/Contact";
import AdminDashboard from "@/pages/AdminDashboard";
import { AddProperty, EditProperty } from "@/pages/PropertyForm";
import NotFound from "@/pages/NotFound";

export default function App() {
  return (
    <Routes>
      <Route element={<MainLayout />}>
        <Route index element={<Home />} />
        <Route path="explore" element={<Explore />} />
        <Route path="properties/:id" element={<PropertyDetails />} />
        <Route element={<ProtectedRoute />}>
  <Route path="assistant" element={<Assistant />} />
  <Route path="compare" element={<Compare />} />
  <Route path="contact" element={<Contact />} />
</Route>
        <Route path="login" element={<Login />} />
        <Route path="register" element={<Register />} />
        <Route element={<ProtectedRoute />}>
          <Route path="favorites" element={<Favorites />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="profile" element={<Profile />} />
        </Route>
        <Route element={<ProtectedRoute admin />}>
          <Route path="admin" element={<AdminDashboard />} />
          <Route path="admin/properties/new" element={<AddProperty />} />
          <Route path="admin/properties/:id/edit" element={<EditProperty />} />
        </Route>
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
}
