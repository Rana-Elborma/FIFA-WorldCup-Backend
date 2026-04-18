class GatePrediction {
  final String gateId;
  final String gateName;
  final double waitMin;
  final String severity; // LOW, MEDIUM, HIGH
  final double crowdLevel; // 0.0 – 1.0
  final String walkTime;

  const GatePrediction({
    required this.gateId,
    required this.gateName,
    required this.waitMin,
    required this.severity,
    required this.crowdLevel,
    required this.walkTime,
  });

  factory GatePrediction.fromMap(Map<String, dynamic> m) {
    return GatePrediction(
      gateId: m['gate_id'].toString(),
      gateName: m['gate'] != null ? m['gate']['name'] as String : 'Gate ${m['gate_id']}',
      waitMin: (m['wait_pred_min'] as num).toDouble(),
      severity: (m['severity'] as String?) ?? 'LOW',
      crowdLevel: (m['crowd_level'] as num?)?.toDouble() ?? 0.3,
      walkTime: (m['walk_time'] as String?) ?? '5 min walk',
    );
  }
}
