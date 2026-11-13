import { BarChart3 } from "lucide-react";
import { ModulePlaceholder } from "@/components/layout/module-placeholder";

export default function AnalyticsPage() {
  return (
    <ModulePlaceholder
      title="Pilotage"
      description="Indicateurs consolidés des demandes, des documents et de l'assistant."
      icon={BarChart3}
      phase={5}
      features={[
        "KPI calculés depuis les données enregistrées",
        "Filtres par période, équipe et catégorie",
        "Fiche de chaque indicateur : définition, formule, source",
        "Mêmes vues SQL que le rapport Power BI",
      ]}
    />
  );
}
