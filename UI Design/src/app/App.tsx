import { useState, useEffect, useCallback } from "react";
import { MainRouteView } from "./components/MainRouteView";
import { CongestionAlertModal } from "./components/CongestionAlertModal";
import { AlternativesView } from "./components/AlternativesView";
import { GateData, View } from "./types";

// Initial gate data
const initialGates: GateData[] = [
  {
    id: 1,
    name: "Gate 1",
    waitTime: 6,
    walkTime: 7,
    distance: 520,
    crowdLevel: "Medium",
  },
  {
    id: 2,
    name: "Gate 2",
    waitTime: 12,
    walkTime: 5,
    distance: 380,
    crowdLevel: "High",
  },
  {
    id: 3,
    name: "Gate 3",
    waitTime: 8,
    walkTime: 6,
    distance: 450,
    crowdLevel: "High",
    isRecommended: true,
  },
  {
    id: 4,
    name: "Gate 4",
    waitTime: 3,
    walkTime: 7,
    distance: 470,
    crowdLevel: "Low",
  },
];

function App() {
  const [gates, setGates] = useState<GateData[]>(initialGates);
  const [currentGate, setCurrentGate] = useState<GateData>(initialGates[2]); // Start with Gate 3
  const [view, setView] = useState<View>("main");
  const [lastUpdate, setLastUpdate] = useState(new Date());
  const [showCongestionAlert, setShowCongestionAlert] = useState(false);
  const [alternativeGate, setAlternativeGate] = useState<GateData | null>(null);
  const [previewingGate, setPreviewingGate] = useState<GateData | null>(null);

  // Simulate real-time updates
  useEffect(() => {
    const interval = setInterval(() => {
      setGates((prevGates) =>
        prevGates.map((gate) => {
          // Randomly update wait times and crowd levels
          const waitChange = Math.floor(Math.random() * 3) - 1; // -1, 0, or 1
          const newWaitTime = Math.max(1, Math.min(15, gate.waitTime + waitChange));

          // Determine crowd level based on wait time
          let newCrowdLevel: "Low" | "Medium" | "High";
          if (newWaitTime <= 4) {
            newCrowdLevel = "Low";
          } else if (newWaitTime <= 8) {
            newCrowdLevel = "Medium";
          } else {
            newCrowdLevel = "High";
          }

          return {
            ...gate,
            waitTime: newWaitTime,
            crowdLevel: newCrowdLevel,
          };
        })
      );
      setLastUpdate(new Date());
    }, 3000); // Update every 3 seconds

    return () => clearInterval(interval);
  }, []);

  // Update current gate data when gates change
  useEffect(() => {
    const updatedCurrentGate = gates.find((g) => g.id === currentGate.id);
    if (updatedCurrentGate) {
      setCurrentGate(updatedCurrentGate);
    }
  }, [gates, currentGate.id]);

  // Check for congestion and show alert
  useEffect(() => {
    if (view === "main" && currentGate.crowdLevel === "High") {
      // Find best alternative (lowest total time with low/medium crowd)
      const alternatives = gates.filter(
        (g) => g.id !== currentGate.id && g.crowdLevel !== "High"
      );

      if (alternatives.length > 0) {
        const bestAlternative = alternatives.reduce((best, gate) => {
          const totalTime = gate.waitTime + gate.walkTime;
          const bestTotalTime = best.waitTime + best.walkTime;
          return totalTime < bestTotalTime ? gate : best;
        });

        setAlternativeGate(bestAlternative);

        // Show alert after a short delay
        const timer = setTimeout(() => {
          setShowCongestionAlert(true);
        }, 2000);

        return () => clearTimeout(timer);
      }
    }
  }, [currentGate, gates, view]);

  const handleAcceptReroute = useCallback(() => {
    if (alternativeGate) {
      setCurrentGate(alternativeGate);
      setShowCongestionAlert(false);
      setAlternativeGate(null);
    }
  }, [alternativeGate]);

  const handleKeepRoute = useCallback(() => {
    setShowCongestionAlert(false);
    setAlternativeGate(null);
  }, []);

  const handleShowAlternatives = useCallback(() => {
    setView("alternatives");
  }, []);

  const handleSelectRoute = useCallback((gate: GateData) => {
    setCurrentGate(gate);
    setView("main");
    setPreviewingGate(null);
  }, []);

  const handlePreviewRoute = useCallback((gate: GateData) => {
    setPreviewingGate(gate);
  }, []);

  const handleCloseAlternatives = useCallback(() => {
    setView("main");
    setPreviewingGate(null);
  }, []);

  const getTimeSinceUpdate = () => {
    const seconds = Math.floor((Date.now() - lastUpdate.getTime()) / 1000);
    if (seconds < 10) {
      return `${seconds} second${seconds !== 1 ? "s" : ""} ago`;
    }
    return "just now";
  };

  return (
    <div className="min-h-screen bg-[#f3f4f6] flex items-center justify-center p-4">
      <div className="relative w-full max-w-[375px] h-[812px] bg-white rounded-[44px] shadow-2xl overflow-hidden">
        {view === "main" && (
          <MainRouteView
            currentGate={currentGate}
            onShowAlternatives={handleShowAlternatives}
            timeSinceUpdate={getTimeSinceUpdate()}
          />
        )}

        {view === "alternatives" && (
          <AlternativesView
            gates={gates}
            currentGate={currentGate}
            previewingGate={previewingGate}
            onSelectRoute={handleSelectRoute}
            onPreviewRoute={handlePreviewRoute}
            onClose={handleCloseAlternatives}
            timeSinceUpdate={getTimeSinceUpdate()}
          />
        )}

        {showCongestionAlert && alternativeGate && (
          <CongestionAlertModal
            currentGate={currentGate}
            alternativeGate={alternativeGate}
            onAccept={handleAcceptReroute}
            onKeep={handleKeepRoute}
          />
        )}
      </div>
    </div>
  );
}

export default App;
