import { AlertCircle, Loader2, type LucideIcon } from "lucide-react";

export function Spinner({ label = "Chargement…" }: { label?: string }) {
  return (
    <div role="status" className="flex items-center justify-center gap-2 py-10 text-muted">
      <Loader2 className="size-4 animate-spin" aria-hidden />
      {label}
    </div>
  );
}

export function ErrorMessage({ message }: { message: string }) {
  return (
    <div
      role="alert"
      className="flex items-start gap-2 rounded-md border border-danger/20 bg-danger-soft px-3 py-2.5 text-danger"
    >
      <AlertCircle className="mt-0.5 size-4 shrink-0" aria-hidden />
      <span>{message}</span>
    </div>
  );
}

export function EmptyState({
  icon: Icon,
  title,
  children,
}: {
  icon: LucideIcon;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center px-6 py-14 text-center">
      <div className="mb-3 rounded-full bg-navy-50 p-3 text-navy-700">
        <Icon className="size-5" aria-hidden />
      </div>
      <h3 className="font-semibold text-ink">{title}</h3>
      <div className="mt-1 max-w-md text-muted">{children}</div>
    </div>
  );
}
