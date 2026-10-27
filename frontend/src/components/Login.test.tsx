import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { AuthProvider } from "@/hooks/useAuth";
import { ToastProvider } from "@/hooks/useToast";
import { Login } from "@/pages/AuthPages";

function renderLogin() {
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter><ToastProvider><AuthProvider><Login /></AuthProvider></ToastProvider></MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("Login form", () => {
  it("shows validation errors and does not call the API when fields are invalid", async () => {
    renderLogin();
    await userEvent.type(screen.getByLabelText(/e-mail/i), "not-an-email");
    await userEvent.click(screen.getByRole("button", { name: /log in/i }));
    expect(await screen.findByText(/valid e-mail/i)).toBeInTheDocument();
    expect(await screen.findByText(/password is required/i)).toBeInTheDocument();
  });
});
