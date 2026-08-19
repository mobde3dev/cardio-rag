import { GuidelineMetadata } from "@/types/rag";

export const INDEXED_GUIDELINES: GuidelineMetadata[] = [
  {
    id: "who-hypertension-2021",
    name: "WHO 2021 Hypertension",
    code: "WHO-2021",
    organization: "WHO",
    year: 2021,
    title: "Guideline for the pharmacological treatment of hypertension in adults",
    scope: "Initial drug classes, single-pill combinations, target BP thresholds, task-sharing & safety",
    totalChunksCount: 310,
    lastUpdated: "2021-08",
  },
  {
    id: "nice-ng238",
    name: "NICE NG238",
    code: "NG238",
    organization: "NICE",
    year: 2023,
    title: "Cardiovascular disease: risk assessment and reduction, including lipid modification",
    scope: "Statin intensity classification, QRISK3 thresholds, primary & secondary prevention, baseline testing",
    totalChunksCount: 380,
    lastUpdated: "2023-12",
  }
];
