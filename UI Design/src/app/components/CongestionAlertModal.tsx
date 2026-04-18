import { AlertTriangle, Clock, Navigation, X } from "lucide-react";
import { GateData } from "../types";

interface CongestionAlertModalProps {
  currentGate: GateData;
  alternativeGate: GateData;
  onAccept: () => void;
  onKeep: () => void;
}

export function CongestionAlertModal({
  currentGate,
  alternativeGate,
  onAccept,
  onKeep,
}: CongestionAlertModalProps) {
  const timeDifference = alternativeGate.waitTime - currentGate.waitTime;
  const distanceDifference = alternativeGate.distance - currentGate.distance;

  return (
    <>
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm z-50 animate-in fade-in duration-300"></div>

      {/* Modal */}
      <div className="absolute top-[100px] left-4 right-4 z-50 animate-in slide-in-from-top duration-300">
        <div className="bg-white rounded-3xl shadow-2xl overflow-hidden">
          {/* Alert Header */}
          <div className="bg-[#fb2c36] px-5 py-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-white/20 rounded-full flex items-center justify-center">
                <AlertTriangle className="w-6 h-6 text-white" />
              </div>
              <div>
                <h3 className="text-white text-lg font-bold">Congestion Ahead</h3>
                <div className="flex items-center gap-2 mt-0.5">
                  <span className="text-white/90 text-sm font-medium">High Severity</span>
                  <span className="text-white/70 text-sm">•</span>
                  <span className="text-white/90 text-sm">{currentGate.name} area</span>
                </div>
              </div>
            </div>
            <button
              onClick={onKeep}
              className="w-8 h-8 flex items-center justify-center hover:bg-white/10 rounded-full transition-colors"
            >
              <X className="w-5 h-5 text-white" />
            </button>
          </div>

          {/* AI Prediction */}
          <div className="bg-[#fef5f5] px-5 py-4 border-b border-[#fee]">
            <div className="flex items-start gap-2">
              <div className="flex-shrink-0 mt-0.5">
                <div className="w-5 h-5 flex items-center justify-center text-[#fb2c36]">🤖</div>
              </div>
              <div>
                <div className="text-[#fb2c36] text-sm font-bold mb-1">AI Prediction</div>
                <p className="text-[#6a7282] text-sm leading-relaxed">
                  Predicted density increasing in the next{" "}
                  <span className="font-semibold text-[#101828]">10–15 minutes</span>
                </p>
              </div>
            </div>
          </div>

          {/* Recommended Action */}
          <div className="bg-[#f0fdf4] px-5 py-4">
            <div className="flex items-start justify-between mb-3">
              <div>
                <div className="text-[#00a63e] text-xs font-medium mb-1">Recommended Action</div>
                <h4 className="text-[#101828] text-lg font-bold">
                  Reroute to {alternativeGate.name}
                </h4>
              </div>
              <div className="bg-[#00a63e] text-white text-xs font-bold px-3 py-1.5 rounded-full">
                FASTER
              </div>
            </div>

            <div className="flex items-center gap-6">
              <div className="flex items-center gap-2">
                <Clock className="w-5 h-5 text-[#00a63e]" />
                <div>
                  <div className="text-[#6a7282] text-xs">New Wait</div>
                  <div className="text-[#101828] text-base font-bold">
                    {alternativeGate.waitTime} min
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <Navigation className="w-5 h-5 text-[#00a63e]" />
                <div>
                  <div className="text-[#6a7282] text-xs">Extra Distance</div>
                  <div className="text-[#101828] text-base font-bold">
                    {distanceDifference > 0 ? "+" : ""}
                    {distanceDifference} m
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="px-5 py-4 space-y-3">
            <button
              onClick={onAccept}
              className="w-full bg-[#00a63e] hover:bg-[#008f35] active:scale-95 transition-all text-white font-bold text-base py-3.5 rounded-2xl shadow-lg shadow-[#00a63e]/25 flex items-center justify-center gap-2"
            >
              <span className="text-lg">✓</span>
              Accept Reroute
            </button>

            <button
              onClick={onKeep}
              className="w-full bg-white hover:bg-[#f9fafb] active:scale-95 transition-all border-2 border-[#e5e7eb] text-[#364153] font-medium text-base py-3.5 rounded-2xl flex items-center justify-center gap-2"
            >
              <X className="w-5 h-5" />
              Keep Current Route
            </button>
          </div>

          {/* Safety Reminder */}
          <div className="bg-[#eff6ff] px-5 py-3 flex items-start gap-2 border-t border-[#dbeafe]">
            <div className="flex-shrink-0 mt-0.5">
              <div className="w-5 h-5 bg-[#155dfc] rounded-full flex items-center justify-center">
                <span className="text-white text-xs font-bold">ℹ</span>
              </div>
            </div>
            <div>
              <div className="text-[#155dfc] text-xs font-bold mb-0.5">Safety Reminder</div>
              <p className="text-[#6a7282] text-xs leading-relaxed">
                Please keep moving and avoid stopping near entrance bottlenecks.
              </p>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
