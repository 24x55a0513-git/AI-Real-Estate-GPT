import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { api, ApiError } from "@/services/api";
import { Button, Card, Field, Input, PageHeader } from "@/components/ui";
import { useAuth } from "@/hooks/useAuth";
import { useToast } from "@/hooks/useToast";

const profileSchema = z.object({
  full_name: z.string().trim().min(2, "Enter your full name").max(120),
  phone: z.string().refine((v) => v === "" || /^\+?[0-9][0-9 \-]{6,18}$/.test(v), "Enter a valid phone number"),
});
const pwSchema = z.object({
  current_password: z.string().min(1, "Required"),
  new_password: z.string().min(8, "At least 8 characters").max(72)
    .refine((v) => /[A-Za-z]/.test(v) && /\d/.test(v), "Use at least one letter and one number"),
});
type P = z.infer<typeof profileSchema>;
type W = z.infer<typeof pwSchema>;

export default function Profile() {
  const { user, setUser } = useAuth();
  const toast = useToast();
  const pf = useForm<P>({ resolver: zodResolver(profileSchema), defaultValues: { full_name: user?.full_name ?? "", phone: user?.phone ?? "" } });
  const pw = useForm<W>({ resolver: zodResolver(pwSchema) });

  const saveProfile = async (v: P) => {
    try { setUser(await api.users.updateProfile({ full_name: v.full_name, phone: v.phone || null })); toast.success("Profile updated"); }
    catch (e) { toast.error(e instanceof ApiError ? e.message : "Update failed"); }
  };
  const savePassword = async (v: W) => {
    try { await api.users.changePassword(v); pw.reset(); toast.success("Password changed"); }
    catch (e) { pw.setError("current_password", { message: e instanceof ApiError ? e.message : "Update failed" }); }
  };

  return (
    <div className="container-page max-w-3xl py-10">
      <PageHeader title="Your profile" subtitle={user?.email} />
      <div className="space-y-6">
        <Card className="p-6"><h2 className="mb-4 text-xl font-semibold">Personal details</h2>
          <form onSubmit={pf.handleSubmit(saveProfile)} className="grid gap-4 sm:grid-cols-2" noValidate>
            <Field label="Full name" htmlFor="p-name" error={pf.formState.errors.full_name?.message}><Input id="p-name" {...pf.register("full_name")} /></Field>
            <Field label="Phone" htmlFor="p-phone" error={pf.formState.errors.phone?.message}><Input id="p-phone" type="tel" {...pf.register("phone")} /></Field>
            <div className="sm:col-span-2"><Button type="submit" variant="gold" loading={pf.formState.isSubmitting}>Save changes</Button></div>
          </form></Card>
        <Card className="p-6"><h2 className="mb-4 text-xl font-semibold">Change password</h2>
          <form onSubmit={pw.handleSubmit(savePassword)} className="grid gap-4 sm:grid-cols-2" noValidate>
            <Field label="Current password" htmlFor="p-cur" error={pw.formState.errors.current_password?.message}><Input id="p-cur" type="password" autoComplete="current-password" {...pw.register("current_password")} /></Field>
            <Field label="New password" htmlFor="p-new" error={pw.formState.errors.new_password?.message}><Input id="p-new" type="password" autoComplete="new-password" {...pw.register("new_password")} /></Field>
            <div className="sm:col-span-2"><Button type="submit" variant="primary" loading={pw.formState.isSubmitting}>Update password</Button></div>
          </form></Card>
      </div>
    </div>
  );
}
