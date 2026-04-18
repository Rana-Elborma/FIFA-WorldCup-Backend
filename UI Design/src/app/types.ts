export type CrowdLevel = "Low" | "Medium" | "High";

export interface GateData {
  id: number;
  name: string;
  waitTime: number; // in minutes
  walkTime: number; // in minutes
  distance: number; // in meters
  crowdLevel: CrowdLevel;
  isRecommended?: boolean;
}

export type View = "main" | "congestion-alert" | "alternatives";
