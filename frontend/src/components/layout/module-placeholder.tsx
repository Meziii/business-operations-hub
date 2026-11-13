import type { LucideIcon } from "lucide-react";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/feedback";
import { PageHeader } from "./page-header";

/** Page d'un module pas encore livré : on dit ce qui arrive et quand, sans contenu factice. */
export function ModulePlaceholder({
  title,
  description,
  icon,
  phase,
  features,
}: {
  title: string;
  description: string;
  icon: LucideIcon;
  phase: number;
  features: string[];
}) {
  return (
    <>
      <PageHeader title={title} description={description} />
      <Card>
        <EmptyState icon={icon} title={`Module prévu en phase ${phase}`}>
          <p>Ce qui arrivera ici :</p>
          <ul className="mt-2 space-y-1 text-left">
            {features.map((f) => (
              <li key={f}>• {f}</li>
            ))}
          </ul>
        </EmptyState>
      </Card>
    </>
  );
}
