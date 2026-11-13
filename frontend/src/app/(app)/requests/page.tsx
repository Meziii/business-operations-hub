import { Inbox } from "lucide-react";
import { ModulePlaceholder } from "@/components/layout/module-placeholder";

export default function RequestsPage() {
  return (
    <ModulePlaceholder
      title="Demandes"
      description="Centraliser, prioriser et suivre les demandes des clients et partenaires."
      icon={Inbox}
      phase={2}
      features={[
        "Création, recherche et filtres (statut, priorité, catégorie, équipe)",
        "Cycle de vie en 7 statuts et échéances SLA",
        "Commentaires, pièces jointes et historique complet",
        "Suggestions de catégorie, priorité et équipe à valider",
      ]}
    />
  );
}
