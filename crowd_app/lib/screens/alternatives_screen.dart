import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../services/location_service.dart';
import '../services/gate_coordinates.dart';
import '../widgets/stadium_map.dart';
import '../widgets/gate_card.dart';

class _GateOption {
  final String id;
  final String name;
  final PreviewGate previewGate;
  final int waitMin;
  final int walkMin;
  final String crowd;
  final bool isRecommended;
  final String? note;
  final int? distanceM;

  const _GateOption({
    required this.id,
    required this.name,
    required this.previewGate,
    required this.waitMin,
    required this.walkMin,
    required this.crowd,
    this.isRecommended = false,
    this.note,
    this.distanceM,
  });
}

class AlternativesScreen extends StatefulWidget {
  const AlternativesScreen({super.key});

  @override
  State<AlternativesScreen> createState() => _AlternativesScreenState();
}

class _AlternativesScreenState extends State<AlternativesScreen> {
  // Fallback static data used when backend is unreachable.
  static const _fallbackGates = [
    _GateOption(id: '1', name: 'Gate 1', previewGate: PreviewGate.gate1, waitMin: 6,  walkMin: 7, crowd: 'Medium', isRecommended: true, note: 'Lowest predicted waiting time', distanceM: 520),
    _GateOption(id: '4', name: 'Gate 4', previewGate: PreviewGate.gate4, waitMin: 7,  walkMin: 7, crowd: 'Medium'),
    _GateOption(id: '2', name: 'Gate 2', previewGate: PreviewGate.gate2, waitMin: 1,  walkMin: 5, crowd: 'Low'),
    _GateOption(id: '3', name: 'Gate 3', previewGate: PreviewGate.gate3, waitMin: 12, walkMin: 10, crowd: 'High'),
  ];

  List<_GateOption> _gates = _fallbackGates;
  String _selectedId = '1';
  bool _loading = true;

  _GateOption get _selected =>
      _gates.firstWhere((g) => g.id == _selectedId);

  _GateOption _buildGateOption({
    required GateCoord coord,
    required dynamic position, // Position? from geolocator
    required int waitMin,
    required String crowd,
    bool isRecommended = false,
    String? note,
  }) {
    int walkMin = coord.walkMinBase;
    int? distanceM;

    if (position != null) {
      final dist = LocationService.distanceTo(position, coord);
      walkMin   = LocationService.walkMinutes(dist);
      distanceM = dist.round();
    }

    final previewMap = {
      1: PreviewGate.gate1,
      2: PreviewGate.gate2,
      3: PreviewGate.gate3,
      4: PreviewGate.gate4,
    };

    return _GateOption(
      id: coord.id.toString(),
      name: coord.name,
      previewGate: previewMap[coord.id] ?? PreviewGate.gate1,
      waitMin: waitMin,
      walkMin: walkMin,
      crowd: crowd,
      isRecommended: isRecommended,
      note: note,
      distanceM: distanceM,
    );
  }

  @override
  void initState() {
    super.initState();
    _fetchGates();
  }

  Future<void> _fetchGates() async {
    final metrics  = await ApiService.fetchMetrics();
    final position = await LocationService.getCurrentPosition();

    if (metrics == null || !mounted) {
      setState(() => _loading = false);
      return;
    }

    final count = (metrics['peoplePred'] as num?)?.toInt() ?? 0;
    final risk  = (metrics['riskLevel'] as String?) ?? 'Normal';
    final baseWait = waitMinFromCount(count);

    // Build gate options with real distances when GPS is available
    final gates = [
      _buildGateOption(
        coord: kGateCoords[3], // Gate 4
        position: position,
        waitMin: (baseWait * 0.5).ceil().clamp(1, 60),
        crowd: 'Low',
        isRecommended: risk != 'Normal',
        note: risk != 'Normal' ? 'Least crowded right now' : null,
      ),
      _buildGateOption(
        coord: kGateCoords[1], // Gate 2
        position: position,
        waitMin: (baseWait * 0.8).ceil().clamp(1, 60),
        crowd: crowdLabelFromRisk(risk) == 'High' ? 'Medium' : 'Low',
        isRecommended: risk == 'Normal',
        note: risk == 'Normal' ? 'Lowest predicted waiting time' : null,
      ),
      _buildGateOption(
        coord: kGateCoords[0], // Gate 1
        position: position,
        waitMin: baseWait,
        crowd: crowdLabelFromRisk(risk),
      ),
      _buildGateOption(
        coord: kGateCoords[2], // Gate 3
        position: position,
        waitMin: (baseWait * 1.5).ceil().clamp(1, 60),
        crowd: risk == 'Normal' ? 'Medium' : 'High',
      ),
    ];

    gates.sort((a, b) => a.waitMin.compareTo(b.waitMin));
    if (mounted) setState(() { _gates = gates; _selectedId = gates.first.id; _loading = false; });
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Scaffold(
        backgroundColor: Color(0xFFF5F6FA),
        body: Center(child: CircularProgressIndicator()),
      );
    }
    return Scaffold(
      backgroundColor: const Color(0xFFF5F6FA),
      body: SafeArea(
        child: Column(
          children: [
            // ── Top bar
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 16, 20, 0),
              child: Row(
                children: [
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: const [
                      Text(
                        'Alternative Routes',
                        style: TextStyle(
                          fontSize: 20,
                          fontWeight: FontWeight.w700,
                          color: Color(0xFF1A1A2E),
                        ),
                      ),
                      SizedBox(height: 4),
                      Row(
                        children: [
                          Icon(Icons.circle, size: 9, color: Color(0xFF43A047)),
                          SizedBox(width: 5),
                          Text(
                            'Live Location ON',
                            style: TextStyle(
                              fontSize: 12,
                              color: Color(0xFF1565C0),
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                  const Spacer(),
                  GestureDetector(
                    onTap: () => Navigator.pop(context),
                    child: Container(
                      width: 34,
                      height: 34,
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(17),
                        border: Border.all(color: const Color(0xFFE0E0E0)),
                      ),
                      child: const Icon(Icons.close,
                          size: 18, color: Color(0xFF424242)),
                    ),
                  ),
                ],
              ),
            ),

            const SizedBox(height: 12),

            // ── Map
            Stack(
              children: [
                SizedBox(
                  height: 200,
                  child: StadiumMap(activeGate: _selected.previewGate),
                ),
                // Previewing label
                Positioned(
                  top: 12,
                  left: 14,
                  child: Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(8),
                      boxShadow: [
                        BoxShadow(
                          color: Colors.black.withOpacity(0.08),
                          blurRadius: 6,
                        ),
                      ],
                    ),
                    child: Text(
                      'Previewing: ${_selected.name}',
                      style: const TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                        color: Color(0xFF1A1A2E),
                      ),
                    ),
                  ),
                ),
              ],
            ),

            // ── Gate list
            Expanded(
              child: ListView(
                padding:
                    const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                children: [
                  for (final g in _gates)
                    GateCard(
                      gateName: g.name,
                      waitMin: g.waitMin,
                      walkMin: g.walkMin,
                      crowd: g.crowd,
                      isRecommended: g.isRecommended,
                      isSelected: g.id == _selectedId,
                      note: g.note,
                      distanceM: g.distanceM,
                      onTap: () => setState(() => _selectedId = g.id),
                    ),
                ],
              ),
            ),

            // ── Select Route button + footer
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
              child: Column(
                children: [
                  SizedBox(
                    width: double.infinity,
                    height: 52,
                    child: ElevatedButton.icon(
                      onPressed: () => Navigator.pop(context, _selectedId),
                      icon: const Icon(Icons.near_me,
                          size: 18, color: Colors.white),
                      label: const Text(
                        'Select Route',
                        style: TextStyle(
                            fontSize: 16,
                            fontWeight: FontWeight.w700,
                            color: Colors.white),
                      ),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: const Color(0xFF1565C0),
                        shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(14)),
                        elevation: 0,
                      ),
                    ),
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    'Updated 0 seconds ago',
                    style: TextStyle(fontSize: 12, color: Color(0xFF9E9E9E)),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
