import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";

import { ApiError } from "@/services/api";
import { Button, Card, Field, Input } from "@/components/ui";
import { useAuth } from "@/hooks/useAuth";
import { useToast } from "@/hooks/useToast";

const PHONE = /^\+?[0-9][0-9\- ]{6,18}$/;

const loginSchema = z.object({
  email: z.string().email("Enter a valid e-mail"),
  password: z.string().min(1, "Password is required"),
});

export const registerSchema = z.object({
  full_name: z.string().trim().min(2, "Enter your full name").max(120),
  email: z.string().email("Enter a valid e-mail"),
  phone: z
    .string()
    .refine((v) => v === "" || PHONE.test(v), "Enter a valid phone number")
    .optional(),
  password: z
    .string()
    .min(8, "At least 8 characters")
    .max(72, "At most 72 characters")
    .refine(
      (v) => /[A-Za-z]/.test(v) && /\d/.test(v),
      "Use at least one letter and one number",
    ),
});

type LoginForm = z.infer<typeof loginSchema>;
type RegisterForm = z.infer<typeof registerSchema>;

function Shell({
  title,
  subtitle,
  children,
  footer,
}: {
  title: string;
  subtitle: string;
  children: React.ReactNode;
  footer: React.ReactNode;
}) {
  return (
    <div className="container-page flex justify-center py-14">
      <Card className="w-full max-w-md p-8">
        <h1 className="text-3xl font-semibold">{title}</h1>
        <p className="mt-1 text-sm text-charcoal-500">{subtitle}</p>

        <div className="mt-6">{children}</div>

        <p className="mt-6 text-center text-sm text-charcoal-500">
          {footer}
        </p>
      </Card>
    </div>
  );
}

export function Login() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const toast = useToast();

  const from =
    (location.state as { from?: string } | null)?.from ?? "/dashboard";

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: "",
      password: "",
    },
  });

  if (user) {
    return <Navigate to={from} replace />;
  }

  const onSubmit = async (v: LoginForm) => {
    try {
      const u = await login(v.email, v.password);

      toast.success(`Welcome back, ${u.full_name.split(" ")[0]}!`);
      navigate(from, { replace: true });
    } catch (e) {
      setError("root", {
        message: e instanceof ApiError ? e.message : "Login failed",
      });
    }
  };

  return (
    <Shell
      title="Welcome back"
      subtitle="Log in to see your favorites, inquiries and chats."
      footer={
        <>
          New here?{" "}
          <Link
            to="/register"
            className="font-medium text-gold-600 hover:underline"
          >
            Create an account
          </Link>
        </>
      }
    >
      <form
        onSubmit={handleSubmit(onSubmit)}
        className="space-y-4"
        autoComplete="off"
        noValidate
      >
        {errors.root && (
          <p
            role="alert"
            className="rounded-lg bg-red-50 p-3 text-sm text-red-700"
          >
            {errors.root.message}
          </p>
        )}

        <Field
          label="E-mail"
          htmlFor="email"
          error={errors.email?.message}
        >
          <Input
            id="email"
            type="email"
            autoComplete="off"
            {...register("email")}
          />
        </Field>

        <Field
          label="Password"
          htmlFor="password"
          error={errors.password?.message}
        >
          <Input
            id="password"
            type="password"
            autoComplete="new-password"
            {...register("password")}
          />
        </Field>

        <Button
          type="submit"
          variant="gold"
          className="w-full"
          loading={isSubmitting}
        >
          Log in
        </Button>
      </form>
    </Shell>
  );
}

export function Register() {
  const { user, register: signUp } = useAuth();
  const navigate = useNavigate();
  const toast = useToast();

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<RegisterForm>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      full_name: "",
      email: "",
      phone: "",
      password: "",
    },
  });

  if (user) {
    return <Navigate to="/dashboard" replace />;
  }

  const onSubmit = async (v: RegisterForm) => {
    try {
      await signUp({
        email: v.email,
        password: v.password,
        full_name: v.full_name,
        phone: v.phone || null,
      });

      toast.success("Account created");
      navigate("/dashboard", { replace: true });
    } catch (e) {
      setError("root", {
        message: e instanceof ApiError ? e.message : "Registration failed",
      });
    }
  };

  return (
    <Shell
      title="Create your account"
      subtitle="Save properties, send inquiries and keep your assistant chats."
      footer={
        <>
          Already registered?{" "}
          <Link
            to="/login"
            className="font-medium text-gold-600 hover:underline"
          >
            Log in
          </Link>
        </>
      }
    >
      <form
        onSubmit={handleSubmit(onSubmit)}
        className="space-y-4"
        autoComplete="off"
        noValidate
      >
        {errors.root && (
          <p
            role="alert"
            className="rounded-lg bg-red-50 p-3 text-sm text-red-700"
          >
            {errors.root.message}
          </p>
        )}

        <Field
          label="Full name"
          htmlFor="full_name"
          error={errors.full_name?.message}
        >
          <Input
            id="full_name"
            autoComplete="name"
            {...register("full_name")}
          />
        </Field>

        <Field
          label="E-mail"
          htmlFor="email"
          error={errors.email?.message}
        >
          <Input
            id="email"
            type="email"
            autoComplete="off"
            {...register("email")}
          />
        </Field>

        <Field
          label="Phone (optional)"
          htmlFor="phone"
          error={errors.phone?.message}
        >
          <Input
            id="phone"
            type="tel"
            autoComplete="tel"
            {...register("phone")}
          />
        </Field>

        <Field
          label="Password"
          htmlFor="password"
          error={errors.password?.message}
          hint="8+ characters with a letter and a number"
        >
          <Input
            id="password"
            type="password"
            autoComplete="new-password"
            {...register("password")}
          />
        </Field>

        <Button
          type="submit"
          variant="gold"
          className="w-full"
          loading={isSubmitting}
        >
          Create account
        </Button>
      </form>
    </Shell>
  );
}
