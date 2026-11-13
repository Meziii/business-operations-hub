import { FileText } from "lucide-react";
import { ModulePlaceholder } from "@/components/layout/module-placeholder";

export default function DocumentsPage() {
  return (
    <ModulePlaceholder
      title="Documents"
      description="Extraire, contrôler et valider les informations des factures et demandes de garantie."
      icon={FileText}
      phase={3}
      features={[
        "Import PDF, extraction du texte et OCR des scans",
        "Champs extraits avec niveau de confiance",
        "Contrôles : champs manquants, doublons, incohérences",
        "Validation humaine et rattachement à une demande",
      ]}
    />
  );
}
