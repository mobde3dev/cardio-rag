import { GuidelineMetadata } from "@/types/rag";

export const INDEXED_GUIDELINES: GuidelineMetadata[] = [
  {
    id: "nice-ng136",
    name: "NICE NG136",
    code: "NG136",
    organization: "NICE",
    year: 2022,
    title: "Hypertension in adults: diagnosis and management",
    scope: "Blood pressure thresholds, step-care medication, monitoring protocols, target BP",
    totalChunksCount: 420,
    lastUpdated: "2023-11",
  },
  {
    id: "who-hypertension-2021",
    name: "WHO 2021 Hypertension",
    code: "WHO-HTN-2021",
    organization: "WHO",
    year: 2021,
    title: "Guideline for the pharmacological treatment of hypertension in adults",
    scope: "Initial single-pill combination therapy, non-physician prescribing, cardiovascular risk assessment",
    totalChunksCount: 310,
    lastUpdated: "2021-08",
  },
  {
    id: "nice-cg181-ng238",
    name: "NICE CG181 / NG238",
    code: "NG238",
    organization: "NICE",
    year: 2023,
    title: "Cardiovascular disease: risk assessment and reduction, including lipid modification",
    scope: "Statin intensity classification, QRISK tool limits, non-statin therapies, baseline testing",
    totalChunksCount: 380,
    lastUpdated: "2023-12",
  }
];
