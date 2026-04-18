class CongestionAlert {
  final String severity; // HIGH, MEDIUM, LOW
  final String area;
  final String prediction;
  final String rerouteGate;
  final int newWaitMin;
  final String extraDistance;

  const CongestionAlert({
    required this.severity,
    required this.area,
    required this.prediction,
    required this.rerouteGate,
    required this.newWaitMin,
    required this.extraDistance,
  });
}
