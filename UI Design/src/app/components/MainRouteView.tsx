import { Clock, Navigation, Users, Info } from "lucide-react";
import { GateData } from "../types";

interface MainRouteViewProps {
  currentGate: GateData;
  onShowAlternatives: () => void;
  timeSinceUpdate: string;
}

export function MainRouteView({
  currentGate,
  onShowAlternatives,
  timeSinceUpdate,
}: MainRouteViewProps) {
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
      <div className="absolute top-[44px] left-0 right-0 bg-white rounded-t-[44px] shadow-sm z-40 pb-4">
        <div className="px-6 pt-6">
          <h1 className="text-2xl font-bold text-[#101828]">Aramco Stadium</h1>
          <div className="flex items-center gap-2 mt-2">
            <div className="w-2 h-2 bg-[#00c950] rounded-full animate-pulse"></div>
            <span className="text-[#155dfc] text-sm font-medium">Live Location ON</span>
          </div>
        </div>

        {/* Notification & User Icons */}
        <div className="absolute top-6 right-6 flex items-center gap-3">
          <button className="relative">
            <div className="w-10 h-10 rounded-full bg-[#f3f4f6] flex items-center justify-center">
              🔔
            </div>
            <div className="absolute top-0 right-0 w-2 h-2 bg-red-500 rounded-full"></div>
          </button>
          <button>
            <div className="w-10 h-10 rounded-full bg-[#f3f4f6] flex items-center justify-center">
              👤
            </div>
          </button>
        </div>
      </div>

      {/* Scrollable Content Container */}
      <div className="absolute top-[135px] left-0 right-0 bottom-0 overflow-y-auto">
        {/* Map Area */}
        <div className="w-full h-[280px] bg-gradient-to-br from-[#eff6ff] to-[#f3f4f6] overflow-hidden">
          <div className="relative w-full h-full flex items-center justify-center">
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

              {/* Alternative Routes - Gray Dashed */}
              {currentGate.id !== 1 && (
                <line
                  x1="60"
                  y1="220"
                  x2="200"
                  y2="75"
                  stroke="#9ca3af"
                  strokeWidth="2"
                  strokeDasharray="6 4"
                  opacity="0.4"
                />
              )}
              {currentGate.id !== 2 && (
                <line
                  x1="60"
                  y1="220"
                  x2="90"
                  y2="105"
                  stroke="#9ca3af"
                  strokeWidth="2"
                  strokeDasharray="6 4"
                  opacity="0.4"
                />
              )}
              {currentGate.id !== 3 && (
                <line
                  x1="60"
                  y1="220"
                  x2="250"
                  y2="125"
                  stroke="#9ca3af"
                  strokeWidth="2"
                  strokeDasharray="6 4"
                  opacity="0.4"
                />
              )}
              {currentGate.id !== 4 && (
                <line
                  x1="60"
                  y1="220"
                  x2="110"
                  y2="115"
                  stroke="#9ca3af"
                  strokeWidth="2"
                  strokeDasharray="6 4"
                  opacity="0.4"
                />
              )}

              {/* Active Route - Solid Blue Line */}
              {currentGate.id === 1 && (
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
              {currentGate.id === 2 && (
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
              {currentGate.id === 3 && (
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
              {currentGate.id === 4 && (
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
                r="8"
                fill={currentGate.id === 1 ? "#3b82f6" : "#6b7280"}
                stroke="white"
                strokeWidth="2.5"
              />

              {/* Gate 2 */}
              <circle
                cx="90"
                cy="105"
                r="8"
                fill={currentGate.id === 2 ? "#3b82f6" : "#6b7280"}
                stroke="white"
                strokeWidth="2.5"
              />

              {/* Gate 3 */}
              <circle
                cx="250"
                cy="125"
                r="9"
                fill={currentGate.id === 3 ? "#3b82f6" : "#6b7280"}
                stroke="white"
                strokeWidth="2.5"
              />

              {/* Gate 4 */}
              <circle
                cx="110"
                cy="115"
                r="8"
                fill={currentGate.id === 4 ? "#3b82f6" : "#6b7280"}
                stroke="white"
                strokeWidth="2.5"
              />
            </svg>

            {/* Gate Labels - Positioned Absolutely */}
            <div className="absolute" style={{ left: "200px", top: "60px", transform: "translate(-50%, 0)" }}>
              <span className="text-[10px] font-medium text-[#1f2937] bg-white/80 px-1.5 py-0.5 rounded">
                Gate 1
              </span>
            </div>
            <div className="absolute" style={{ left: "90px", top: "90px", transform: "translate(-50%, 0)" }}>
              <span className="text-[10px] font-medium text-[#1f2937] bg-white/80 px-1.5 py-0.5 rounded">
                Gate 2
              </span>
            </div>
            <div className="absolute" style={{ left: "250px", top: "110px", transform: "translate(-50%, 0)" }}>
              <span className="text-[10px] font-medium text-[#1f2937] bg-white/80 px-1.5 py-0.5 rounded">
                Gate 3
              </span>
            </div>
            <div className="absolute" style={{ left: "110px", top: "100px", transform: "translate(-50%, 0)" }}>
              <span className="text-[10px] font-medium text-[#1f2937] bg-white/80 px-1.5 py-0.5 rounded">
                Gate 4
              </span>
            </div>

            {/* Legend */}
            <div className="absolute top-10 left-4 bg-white/95 backdrop-blur-sm rounded-2xl shadow-lg p-3 space-y-2">
              <div className="flex items-center gap-2">
                <div className="w-6 h-0.5 bg-[#3b82f6] rounded"></div>
                <span className="text-[11px] text-[#364153]">Recommended</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-6 h-0.5 bg-[#9ca3af] rounded" style={{ backgroundImage: "repeating-linear-gradient(to right, #9ca3af 0, #9ca3af 4px, transparent 4px, transparent 8px)" }}></div>
                <span className="text-[11px] text-[#364153]">Alternative</span>
              </div>
            </div>

            {/* Compass Button */}
            <button className="absolute bottom-4 right-4 w-12 h-12 bg-white rounded-full shadow-lg flex items-center justify-center hover:scale-105 active:scale-95 transition-all">
              <Navigation className="w-6 h-6 text-[#364153]" />
            </button>
          </div>
        </div>

        {/* Gate Recommendation Card - Directly Below Map */}
        <div className="px-4 pt-4 bg-white">
          <div className="bg-gradient-to-br from-[#eff6ff] to-white border border-[#dbeafe] rounded-2xl shadow-lg p-4 space-y-3">
            {/* Header */}
            <div className="flex items-start justify-between">
              <div>
                <div className="text-[#6a7282] text-xs mb-1">Recommended Gate</div>
                <div className="text-[#101828] text-2xl font-bold">{currentGate.name}</div>
              </div>
              <div className="bg-[#dcfce7] px-3 py-1.5 rounded-lg flex items-center gap-1.5">
                <div className="w-4 h-4 flex items-center justify-center text-[#008236]">✓</div>
                <span className="text-[#008236] text-xs font-medium">High confidence</span>
              </div>
            </div>

            {/* Metrics */}
            <div className="flex items-center justify-between">
              <div className="flex items-start gap-2">
                <div className="w-9 h-9 bg-white rounded-xl flex items-center justify-center">
                  <Clock className="w-5 h-5 text-[#155dfc]" />
                </div>
                <div>
                  <div className="text-[#6a7282] text-xs">Wait Time</div>
                  <div className="text-[#101828] text-base font-bold">
                    {currentGate.waitTime} min
                  </div>
                </div>
              </div>

              <div className="flex items-start gap-2">
                <div className="w-9 h-9 bg-white rounded-xl flex items-center justify-center">
                  <Navigation className="w-5 h-5 text-[#155dfc]" />
                </div>
                <div>
                  <div className="text-[#6a7282] text-xs">Distance</div>
                  <div className="text-[#101828] text-base font-bold">
                    {currentGate.walkTime} min walk
                  </div>
                </div>
              </div>
            </div>

            {/* Crowd Level */}
            <div className="bg-white rounded-xl p-3 space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                  <Users className="w-4 h-4 text-[#6a7282]" />
                  <span className="text-[#4a5565] text-xs">Crowd Level</span>
                </div>
                <span className="text-[#101828] text-xs font-bold">{currentGate.crowdLevel}</span>
              </div>
              <div className="relative w-full h-2.5 bg-[#f3f4f6] rounded-full overflow-hidden">
                <div
                  className={`absolute left-0 top-0 h-full ${getCrowdColor(
                    currentGate.crowdLevel
                  )} rounded-full transition-all duration-500`}
                  style={{ width: getCrowdWidth(currentGate.crowdLevel) }}
                ></div>
              </div>
            </div>
          </div>
        </div>

        {/* Action Buttons - Immediately Follow Card */}
        <div className="px-4 pt-4 pb-20 bg-white space-y-3">
          <button className="w-full bg-[#155dfc] hover:bg-[#1247d6] active:scale-95 transition-all text-white font-bold text-base py-3.5 rounded-2xl shadow-lg shadow-[#155dfc]/25 flex items-center justify-center gap-2">
            <Navigation className="w-5 h-5" />
            Start Navigation
          </button>

          <div className="flex gap-3">
            <button
              onClick={onShowAlternatives}
              className="flex-1 bg-white hover:bg-[#f9fafb] active:scale-95 transition-all border border-[#e5e7eb] text-[#364153] font-normal text-base py-3.5 rounded-2xl flex items-center justify-center gap-2"
            >
              <div className="w-5 h-5 flex items-center justify-center">☰</div>
              Alternatives
            </button>

            <button className="w-14 bg-white hover:bg-[#f9fafb] active:scale-95 transition-all border border-[#e5e7eb] rounded-2xl flex items-center justify-center">
              <Info className="w-5 h-5 text-[#364153]" />
            </button>
          </div>

          {/* Update Time */}
          <div className="text-center text-[#6a7282] text-xs pt-2">Updated {timeSinceUpdate}</div>
        </div>
      </div>

      {/* Home Indicator */}
      <div className="absolute bottom-2 left-1/2 -translate-x-1/2 w-32 h-1 bg-black rounded-full z-50"></div>
    </div>
  );
}