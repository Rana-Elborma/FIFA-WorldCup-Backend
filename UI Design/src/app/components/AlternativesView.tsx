import { Check, Clock, Navigation, Users, X } from "lucide-react";
import { GateData } from "../types";

interface AlternativesViewProps {
  gates: GateData[];
  currentGate: GateData;
  previewingGate: GateData | null;
  onSelectRoute: (gate: GateData) => void;
  onPreviewRoute: (gate: GateData) => void;
  onClose: () => void;
  timeSinceUpdate: string;
}

export function AlternativesView({
  gates,
  currentGate,
  previewingGate,
  onSelectRoute,
  onPreviewRoute,
  onClose,
  timeSinceUpdate,
}: AlternativesViewProps) {
  // Sort gates by total time (wait + walk)
  const sortedGates = [...gates].sort((a, b) => {
    const totalA = a.waitTime + a.walkTime;
    const totalB = b.waitTime + b.walkTime;
    return totalA - totalB;
  });

  // Find the best alternative (lowest total time)
  const bestAlternative = sortedGates[0];

  const getCrowdColor = (level: string) => {
    switch (level) {
      case "Low":
        return "bg-[#00c950]";
      case "Medium":
        return "bg-[#f0b100]";
      case "High":
        return "bg-[#fb2c36]";
      default:
        return "bg-gray-400";
    }
  };

  const getCrowdWidth = (level: string) => {
    switch (level) {
      case "Low":
        return "33%";
      case "Medium":
        return "66%";
      case "High":
        return "100%";
      default:
        return "0%";
    }
  };

  const displayGate = previewingGate || currentGate;

  return (
    <div className="relative w-full h-full bg-white">
      {/* Status Bar */}
      <div className="absolute top-0 left-0 right-0 h-[44px] z-50">
        <div className="flex items-center justify-between px-5 pt-3">
          <div className="text-[15px] font-semibold">9:41</div>
          <div className="flex items-center gap-1">
            <div className="text-xs">📶</div>
            <div className="text-xs">📡</div>
            <div className="text-xs">🔋</div>
          </div>
        </div>
      </div>

      {/* Header */}
      <div className="absolute top-[44px] left-0 right-0 bg-white border-b border-[#e5e7eb] z-40 pb-4">
        <div className="px-6 pt-6 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-[#101828]">Alternative Routes</h1>
            <div className="flex items-center gap-2 mt-1">
              <div className="w-2 h-2 bg-[#00c950] rounded-full animate-pulse"></div>
              <span className="text-[#155dfc] text-sm font-medium">Live Location ON</span>
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-10 h-10 rounded-full bg-[#f3f4f6] hover:bg-[#e5e7eb] active:scale-95 transition-all flex items-center justify-center"
          >
            <X className="w-5 h-5 text-[#364153]" />
          </button>
        </div>
      </div>

      {/* Map Preview */}
      <div className="absolute top-[135px] left-0 right-0 h-[280px] bg-gradient-to-br from-[#eff6ff] to-[#f3f4f6] overflow-hidden border-b border-[#e5e7eb]">
        <div className="relative w-full h-full flex items-center justify-center">
          {previewingGate && (
            <div className="absolute top-4 left-4 bg-white/95 backdrop-blur-sm rounded-xl shadow-md px-3 py-2 z-10">
              <span className="text-[#6a7282] text-xs">
                Previewing: <span className="font-bold text-[#101828]">{previewingGate.name}</span>
              </span>
            </div>
          )}

          {/* SVG Container for Routes and Map */}
          <svg className="absolute inset-0 w-full h-full" viewBox="0 0 375 280">
            {/* Stadium Oval - Dashed Border */}
            <ellipse
              cx="200"
              cy="130"
              rx="140"
              ry="90"
              fill="none"
              stroke="#6b7280"
              strokeWidth="2"
              strokeDasharray="8 4"
              opacity="0.5"
            />

            {/* Alternative Routes - Gray Dashed (not selected) */}
            {displayGate.id !== 1 && (
              <line
                x1="60"
                y1="220"
                x2="200"
                y2="75"
                stroke="#9ca3af"
                strokeWidth="2"
                strokeDasharray="6 4"
                opacity="0.3"
              />
            )}
            {displayGate.id !== 2 && (
              <line
                x1="60"
                y1="220"
                x2="90"
                y2="105"
                stroke="#9ca3af"
                strokeWidth="2"
                strokeDasharray="6 4"
                opacity="0.3"
              />
            )}
            {displayGate.id !== 3 && (
              <line
                x1="60"
                y1="220"
                x2="250"
                y2="125"
                stroke="#9ca3af"
                strokeWidth="2"
                strokeDasharray="6 4"
                opacity="0.3"
              />
            )}
            {displayGate.id !== 4 && (
              <line
                x1="60"
                y1="220"
                x2="110"
                y2="115"
                stroke="#9ca3af"
                strokeWidth="2"
                strokeDasharray="6 4"
                opacity="0.3"
              />
            )}

            {/* Active Route - Solid Blue Line */}
            {displayGate.id === 1 && (
              <line
                x1="60"
                y1="220"
                x2="200"
                y2="75"
                stroke="#3b82f6"
                strokeWidth="4"
                strokeLinecap="round"
              />
            )}
            {displayGate.id === 2 && (
              <line
                x1="60"
                y1="220"
                x2="90"
                y2="105"
                stroke="#3b82f6"
                strokeWidth="4"
                strokeLinecap="round"
              />
            )}
            {displayGate.id === 3 && (
              <line
                x1="60"
                y1="220"
                x2="250"
                y2="125"
                stroke="#3b82f6"
                strokeWidth="4"
                strokeLinecap="round"
              />
            )}
            {displayGate.id === 4 && (
              <line
                x1="60"
                y1="220"
                x2="110"
                y2="115"
                stroke="#3b82f6"
                strokeWidth="4"
                strokeLinecap="round"
              />
            )}

            {/* User Location - Pulsing Blue Circle */}
            <circle cx="60" cy="220" r="12" fill="#3b82f6" opacity="0.2">
              <animate
                attributeName="r"
                from="12"
                to="20"
                dur="1.5s"
                repeatCount="indefinite"
              />
              <animate
                attributeName="opacity"
                from="0.3"
                to="0"
                dur="1.5s"
                repeatCount="indefinite"
              />
            </circle>
            <circle cx="60" cy="220" r="9" fill="#3b82f6" stroke="white" strokeWidth="3" />

            {/* Gate 1 */}
            <circle
              cx="200"
              cy="75"
              r={displayGate.id === 1 ? "10" : "7"}
              fill={displayGate.id === 1 ? "#3b82f6" : "#6b7280"}
              stroke="white"
              strokeWidth="2.5"
            />

            {/* Gate 2 */}
            <circle
              cx="90"
              cy="105"
              r={displayGate.id === 2 ? "10" : "7"}
              fill={displayGate.id === 2 ? "#3b82f6" : "#6b7280"}
              stroke="white"
              strokeWidth="2.5"
            />

            {/* Gate 3 */}
            <circle
              cx="250"
              cy="125"
              r={displayGate.id === 3 ? "10" : "7"}
              fill={displayGate.id === 3 ? "#3b82f6" : "#6b7280"}
              stroke="white"
              strokeWidth="2.5"
            />

            {/* Gate 4 */}
            <circle
              cx="110"
              cy="115"
              r={displayGate.id === 4 ? "10" : "7"}
              fill={displayGate.id === 4 ? "#3b82f6" : "#6b7280"}
              stroke="white"
              strokeWidth="2.5"
            />
          </svg>

          {/* Gate Labels - Positioned Absolutely */}
          <div className="absolute" style={{ left: "200px", top: "60px", transform: "translate(-50%, 0)" }}>
            <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${
              displayGate.id === 1 
                ? "text-[#1f2937] bg-white/90" 
                : "text-[#6b7280] bg-white/70"
            }`}>
              Gate 1
            </span>
          </div>
          <div className="absolute" style={{ left: "90px", top: "90px", transform: "translate(-50%, 0)" }}>
            <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${
              displayGate.id === 2 
                ? "text-[#1f2937] bg-white/90" 
                : "text-[#6b7280] bg-white/70"
            }`}>
              Gate 2
            </span>
          </div>
          <div className="absolute" style={{ left: "250px", top: "110px", transform: "translate(-50%, 0)" }}>
            <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${
              displayGate.id === 3 
                ? "text-[#1f2937] bg-white/90" 
                : "text-[#6b7280] bg-white/70"
            }`}>
              Gate 3
            </span>
          </div>
          <div className="absolute" style={{ left: "110px", top: "100px", transform: "translate(-50%, 0)" }}>
            <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${
              displayGate.id === 4 
                ? "text-[#1f2937] bg-white/90" 
                : "text-[#6b7280] bg-white/70"
            }`}>
              Gate 4
            </span>
          </div>

          {/* Compass Button */}
          <button className="absolute bottom-4 right-4 w-12 h-12 bg-white rounded-full shadow-lg flex items-center justify-center hover:scale-105 active:scale-95 transition-all z-10">
            <Navigation className="w-6 h-6 text-[#364153]" />
          </button>
        </div>
      </div>

      {/* Routes List */}
      <div className="absolute top-[415px] left-0 right-0 bottom-[110px] overflow-y-auto px-4 space-y-3 pb-4">
        {sortedGates.map((gate) => {
          const isRecommended = gate.id === bestAlternative.id;
          const isCurrent = gate.id === currentGate.id;
          const isPreviewing = previewingGate?.id === gate.id;

          return (
            <button
              key={gate.id}
              onClick={() => onPreviewRoute(gate)}
              className={`w-full text-left rounded-2xl p-4 transition-all transform active:scale-95 ${
                isPreviewing
                  ? "bg-[#eff6ff] border-2 border-[#2b7fff] shadow-lg"
                  : "bg-white border border-[#e5e7eb] hover:border-[#2b7fff] hover:shadow-md"
              }`}
            >
              {/* Header */}
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <h3 className="text-[#101828] text-lg font-bold">{gate.name}</h3>
                  {isRecommended && (
                    <div className="bg-[#00a63e] text-white text-[10px] font-bold px-2 py-1 rounded-full flex items-center gap-1">
                      <Check className="w-3 h-3" />
                      Recommended
                    </div>
                  )}
                </div>
                <div
                  className={`w-6 h-6 rounded-full border-2 flex items-center justify-center transition-all ${
                    isPreviewing
                      ? "bg-[#155dfc] border-[#155dfc]"
                      : "bg-white border-[#d1d5dc]"
                  }`}
                >
                  {isPreviewing && <div className="w-3 h-3 bg-white rounded-full"></div>}
                </div>
              </div>

              {isRecommended && (
                <div className="mb-3 flex items-center gap-1.5 text-[#008236] text-xs">
                  <Check className="w-3 h-3" />
                  Lowest predicted waiting time
                </div>
              )}

              {/* Metrics */}
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-1.5">
                  <Clock className="w-3.5 h-3.5 text-[#99a1af]" />
                  <div>
                    <div className="text-[#6a7282] text-[10px]">Wait</div>
                    <div className="text-[#101828] text-sm font-bold">{gate.waitTime} min</div>
                  </div>
                </div>

                <div className="flex items-center gap-1.5">
                  <Navigation className="w-3.5 h-3.5 text-[#99a1af]" />
                  <div>
                    <div className="text-[#6a7282] text-[10px]">Walk</div>
                    <div className="text-[#101828] text-sm font-bold">{gate.walkTime} min</div>
                  </div>
                </div>

                <div className="flex items-center gap-1.5">
                  <Users className="w-3.5 h-3.5 text-[#99a1af]" />
                  <div>
                    <div className="text-[#6a7282] text-[10px]">Crowd</div>
                    <div className="text-[#101828] text-sm font-bold">{gate.crowdLevel}</div>
                  </div>
                </div>
              </div>

              {/* Progress Bar */}
              <div className="relative w-full h-2 bg-[#dddfe2] rounded-full overflow-hidden">
                <div
                  className={`absolute left-0 top-0 h-full ${getCrowdColor(
                    gate.crowdLevel
                  )} rounded-full transition-all duration-500`}
                  style={{ width: getCrowdWidth(gate.crowdLevel) }}
                ></div>
              </div>

              <div className="text-[#6a7282] text-xs mt-2">{gate.distance} m distance</div>
            </button>
          );
        })}
      </div>

      {/* Bottom Actions */}
      <div className="absolute bottom-0 left-0 right-0 bg-white border-t border-[#e5e7eb] px-4 py-4 space-y-3">
        <button
          onClick={() => {
            if (previewingGate) {
              onSelectRoute(previewingGate);
            }
          }}
          disabled={!previewingGate}
          className={`w-full font-bold text-base py-3.5 rounded-2xl shadow-lg flex items-center justify-center gap-2 transition-all ${
            previewingGate
              ? "bg-[#155dfc] hover:bg-[#1247d6] active:scale-95 text-white shadow-[#155dfc]/25"
              : "bg-[#e5e7eb] text-[#9ca3af] cursor-not-allowed"
          }`}
        >
          <Navigation className="w-5 h-5" />
          Select Route
        </button>

        <div className="text-center text-[#6a7282] text-xs">Updated {timeSinceUpdate}</div>
      </div>

      {/* Home Indicator */}
      <div className="absolute bottom-2 left-1/2 -translate-x-1/2 w-32 h-1 bg-black rounded-full"></div>
    </div>
  );
}