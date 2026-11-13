import { cn } from "@/lib/utils";

export function Input({ className, ...props }: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        "h-9 w-full rounded-md border border-line bg-surface px-3 text-ink placeholder:text-muted/70",
        "focus:border-navy-600 focus:outline-none focus:ring-2 focus:ring-navy-100 aria-invalid:border-danger",
        className,
      )}
      {...props}
    />
  );
}

export function Label({ className, ...props }: React.LabelHTMLAttributes<HTMLLabelElement>) {
  return <label className={cn("mb-1.5 block font-medium text-ink", className)} {...props} />;
}

export function Select({ className, ...props }: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      className={cn(
        "h-9 w-full rounded-md border border-line bg-surface px-2.5 text-ink",
        "focus:border-navy-600 focus:outline-none focus:ring-2 focus:ring-navy-100 disabled:bg-canvas disabled:text-muted",
        className,
      )}
      {...props}
    />
  );
}

export function Textarea({ className, ...props }: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      className={cn(
        "w-full rounded-md border border-line bg-surface px-3 py-2 text-ink placeholder:text-muted/70",
        "focus:border-navy-600 focus:outline-none focus:ring-2 focus:ring-navy-100",
        className,
      )}
      {...props}
    />
  );
}
