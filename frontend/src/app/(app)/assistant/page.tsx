import { Bot } from "lucide-react";
import { ModulePlaceholder } from "@/components/layout/module-placeholder";

export default function AssistantPage() {
  return (
    <ModulePlaceholder
      title="Assistant"
      description="Répondre aux questions à partir de la documentation interne, avec les sources."
      icon={Bot}
      phase={4}
      features={[
        "Questions en langage naturel sur les procédures",
        "Réponses citant le document et la page",
        "Refus explicite quand l'information manque",
        "Historique des conversations et avis sur les réponses",
      ]}
    />
  );
}
