import 'package:flutter/material.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:geolocator/geolocator.dart';
import 'dart:async';
import '../models/alert_model.dart';
import '../services/api_service.dart';
import '../services/location_service.dart';
import '../services/gate_coordinates.dart';
import '../widgets/stadium_map.dart';
import 'alert_screen.dart';
import 'alternatives_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final _db = Supabase.instance.client;
  Timer? _timer;
  RealtimeChannel? _alertChannel;
  bool _loading = true;
  bool _hasError = false;
  String _lastUpdated = 'just now';

  String _recGateName = 'Gate 2';
  int _waitMin = 1;
  String _walkTime = '5 min walk';
  String _crowdLevel = 'Low';
  double _crowdFill = 0.20;
  bool _highConfidence = true;
  PreviewGate _activeGate = PreviewGate.gate2;
  bool _gpsActive = false;
  Position? _userPosition;

  @override
  void initState() {
    super.initState();
    _initGps();
    _fetch();
    _timer = Timer.periodic(const Duration(seconds: 5), (_) => _fetch());
    _subscribeToAlerts();
  }

  Future<void> _initGps() async {
    final pos = await LocationService.getCurrentPosition();
    if (pos != null && mounted) {
      setState(() { _userPosition = pos; _gpsActive = true; });
      // Save encrypted GPS to Supabase
      await LocationService.saveGpsToSupabase(
        pos,
        stadiumId: 1,
        zoneId: 1,
        nearestGateId: 1,
        sessionId: Supabase.instance.client.auth.currentSession?.user.id ?? 'anonymous',
      );
    }
  }

  void _subscribeToAlerts() {
    // Alert data is AES-256 encrypted in the database — severity cannot be
    // read directly. Any row inserted into alert is already HIGH severity
    // (the backend only inserts alerts when threshold is exceeded).
    _alertChannel = _db
        .channel('public:alert')
        .onPostgresChanges(
          event: PostgresChangeEvent.insert,
          schema: 'public',
          table: 'alert',
          callback: (payload) {
            if (mounted) _showAlert();
          },
        )
        .subscribe();
  }

  Future<void> _fetch() async {
    // Try the AI backend first (real-time data).
    final metrics = await ApiService.fetchMetrics();
    if (metrics != null && mounted) {
      final risk  = (metrics['riskLevel'] as String?) ?? 'Normal';
      final count = (metrics['peoplePred'] as num?)?.toInt() ?? 0;
      final gate  = _bestGate(risk);

      // Real walk time from GPS distance, or fallback to base value
      String walkTime = '${gate.walkMinBase} min walk';
      if (_userPosition != null) {
        final dist = LocationService.distanceTo(_userPosition!, gate);
        final mins = LocationService.walkMinutes(dist);
        walkTime = '$mins min walk (${dist.round()} m)';
      }

      setState(() {
        _recGateName = gate.name;
        _waitMin     = waitMinFromCount(count);
        _walkTime    = walkTime;
        _crowdLevel  = crowdLabelFromRisk(risk);
        _crowdFill   = crowdFillFromRisk(risk);
        _highConfidence = risk == 'Normal';
        _activeGate  = _previewGateFor(gate.id);
        _hasError    = false;
        _loading     = false;
        _lastUpdated = 'just now';
      });
      return;
    }

    // Backend unreachable — show error indicator, keep last known values.
    if (mounted) setState(() { _hasError = true; _loading = false; });
  }

  // Picks best gate using real GPS distance + crowd level.
  // Falls back to crowd-only recommendation if GPS unavailable.
  GateCoord _bestGate(String risk) {
    if (_userPosition != null) {
      return LocationService.bestGate(_userPosition!, risk);
    }
    // GPS not available — pick by crowd level only
    switch (risk) {
      case 'Critical': return kGateCoords[3]; // Gate 4
      case 'Busy':     return kGateCoords[1]; // Gate 2
      default:         return kGateCoords[2]; // Gate 3
    }
  }

  PreviewGate _previewGateFor(int gateId) {
    switch (gateId) {
      case 1: return PreviewGate.gate1;
      case 2: return PreviewGate.gate2;
      case 4: return PreviewGate.gate4;
      default: return PreviewGate.gate3;
    }
  }

  Color get _crowdBarColor {
    switch (_crowdLevel) {
      case 'High':
        return const Color(0xFFE53935);
      case 'Medium':
        return const Color(0xFFFFA726);
      default:
        return const Color(0xFF43A047);
    }
  }

  void _showAlert() {
    showDialog(
      context: context,
      barrierColor: Colors.black54,
      builder: (_) => AlertScreen(
        alert: const CongestionAlert(
          severity: 'HIGH',
          area: 'Gate 3 area',
          prediction: 'Predicted density increasing in the next 10–15 minutes',
          rerouteGate: 'Gate 4',
          newWaitMin: 5,
          extraDistance: '+20 m',
        ),
        onAccept: () {
          Navigator.pop(context);
          setState(() {
            _recGateName = 'Gate 4';
            _waitMin = 5;
            _crowdLevel = 'Medium';
            _crowdFill = 0.55;
            _activeGate = PreviewGate.gate4;
          });
          ScaffoldMessenger.of(
            context,
          ).showSnackBar(const SnackBar(content: Text('Rerouted to Gate 4')));
        },
        onKeep: () => Navigator.pop(context),
      ),
    );
  }

  void _showAlternatives() async {
    final selected = await Navigator.push<String>(
      context,
      MaterialPageRoute(builder: (_) => const AlternativesScreen()),
    );
    if (selected != null && mounted) {
      // update display based on selection
      final names = {
        '1': 'Gate 1',
        '2': 'Gate 2',
        '3': 'Gate 3',
        '4': 'Gate 4',
      };
      final gates = {
        '1': PreviewGate.gate1,
        '2': PreviewGate.gate2,
        '3': PreviewGate.gate3,
        '4': PreviewGate.gate4,
      };
      setState(() {
        _recGateName = names[selected] ?? 'Gate $selected';
        _activeGate = gates[selected] ?? PreviewGate.gate2;
      });
    }
  }

  @override
  void dispose() {
    _timer?.cancel();
    if (_alertChannel != null) _db.removeChannel(_alertChannel!);
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Scaffold(
        backgroundColor: Colors.white,
        body: Center(child: CircularProgressIndicator()),
      );
    }

    return Scaffold(
      backgroundColor: const Color(0xFFF5F6FA),
      body: SafeArea(
        child: Column(
          children: [
            // ── App bar
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 16, 20, 8),
              child: Row(
                children: [
                  const Expanded(
                    child: Text(
                      'Aramco Stadium',
                      style: TextStyle(
                        fontSize: 22,
                        fontWeight: FontWeight.w800,
                        color: Color(0xFF1A1A2E),
                      ),
                    ),
                  ),
                  // Notification bell
                  GestureDetector(
                    onTap: _showAlert,
                    child: Stack(
                      clipBehavior: Clip.none,
                      children: [
                        Container(
                          width: 40,
                          height: 40,
                          decoration: BoxDecoration(
                            color: Colors.white,
                            shape: BoxShape.circle,
                            border: Border.all(color: const Color(0xFFE0E0E0)),
                          ),
                          child: const Icon(
                            Icons.notifications_outlined,
                            size: 20,
                            color: Color(0xFF424242),
                          ),
                        ),
                        Positioned(
                          top: 0,
                          right: 0,
                          child: Container(
                            width: 10,
                            height: 10,
                            decoration: const BoxDecoration(
                              color: Color(0xFFE53935),
                              shape: BoxShape.circle,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 8),
                  // Profile
                  Container(
                    width: 40,
                    height: 40,
                    decoration: BoxDecoration(
                      color: const Color(0xFFEDE7F6),
                      shape: BoxShape.circle,
                      border: Border.all(color: const Color(0xFFE0E0E0)),
                    ),
                    child: const Icon(
                      Icons.person_outline,
                      size: 20,
                      color: Color(0xFF6A1B9A),
                    ),
                  ),
                ],
              ),
            ),

            // ── Live location indicator
            Padding(
              padding: const EdgeInsets.only(left: 20, bottom: 10),
              child: Row(
                children: [
                  Container(
                    width: 9,
                    height: 9,
                    decoration: BoxDecoration(
                      color: _gpsActive
                          ? const Color(0xFF43A047)
                          : const Color(0xFF9E9E9E),
                      shape: BoxShape.circle,
                    ),
                  ),
                  const SizedBox(width: 6),
                  Text(
                    _gpsActive ? 'Live Location ON' : 'Live Location OFF',
                    style: TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w500,
                      color: _gpsActive
                          ? const Color(0xFF1565C0)
                          : const Color(0xFF9E9E9E),
                    ),
                  ),
                  if (_hasError) ...[
                    const SizedBox(width: 8),
                    const Icon(Icons.wifi_off, size: 14, color: Colors.orange),
                  ],
                ],
              ),
            ),

            // ── Map
            Stack(
              children: [
                SizedBox(
                  height: 210,
                  child: StadiumMap(activeGate: _activeGate),
                ),
                // Legend
                Positioned(
                  top: 12,
                  left: 14,
                  child: Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 10,
                      vertical: 8,
                    ),
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
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: const [
                            _LegendLine(
                              color: Color(0xFF1565C0),
                              dashed: false,
                            ),
                            SizedBox(width: 6),
                            Text(
                              'Recommended',
                              style: TextStyle(
                                fontSize: 11,
                                color: Color(0xFF424242),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 4),
                        Row(
                          children: const [
                            _LegendLine(color: Color(0xFF9E9E9E), dashed: true),
                            SizedBox(width: 6),
                            Text(
                              'Alternative',
                              style: TextStyle(
                                fontSize: 11,
                                color: Color(0xFF424242),
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),

            const SizedBox(height: 10),

            // ── Bottom card
            Expanded(
              child: SingleChildScrollView(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: Column(
                  children: [
                    // Recommendation card
                    Container(
                      width: double.infinity,
                      padding: const EdgeInsets.all(18),
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(16),
                        boxShadow: [
                          BoxShadow(
                            color: Colors.black.withOpacity(0.05),
                            blurRadius: 10,
                            offset: const Offset(0, 2),
                          ),
                        ],
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          // Label + confidence badge
                          Row(
                            children: [
                              const Text(
                                'Recommended Gate',
                                style: TextStyle(
                                  fontSize: 13,
                                  color: Color(0xFF9E9E9E),
                                ),
                              ),
                              const Spacer(),
                              if (_highConfidence)
                                Container(
                                  padding: const EdgeInsets.symmetric(
                                    horizontal: 10,
                                    vertical: 4,
                                  ),
                                  decoration: BoxDecoration(
                                    color: const Color(0xFFF1F8E9),
                                    borderRadius: BorderRadius.circular(20),
                                    border: Border.all(
                                      color: const Color(0xFF81C784),
                                    ),
                                  ),
                                  child: const Row(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      Icon(
                                        Icons.check,
                                        size: 12,
                                        color: Color(0xFF2E7D32),
                                      ),
                                      SizedBox(width: 4),
                                      Text(
                                        'High confidence',
                                        style: TextStyle(
                                          fontSize: 11,
                                          color: Color(0xFF2E7D32),
                                          fontWeight: FontWeight.w600,
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                            ],
                          ),
                          const SizedBox(height: 6),
                          Text(
                            _recGateName,
                            style: const TextStyle(
                              fontSize: 28,
                              fontWeight: FontWeight.w800,
                              color: Color(0xFF1A1A2E),
                            ),
                          ),
                          const SizedBox(height: 14),

                          // Wait + distance row
                          Row(
                            children: [
                              const Icon(
                                Icons.access_time_rounded,
                                size: 16,
                                color: Color(0xFF1565C0),
                              ),
                              const SizedBox(width: 6),
                              Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  const Text(
                                    'Wait Time',
                                    style: TextStyle(
                                      fontSize: 11,
                                      color: Color(0xFF9E9E9E),
                                    ),
                                  ),
                                  Text(
                                    '$_waitMin min',
                                    style: const TextStyle(
                                      fontSize: 16,
                                      fontWeight: FontWeight.w700,
                                      color: Color(0xFF1A1A2E),
                                    ),
                                  ),
                                ],
                              ),
                              const SizedBox(width: 32),
                              const Icon(
                                Icons.near_me_outlined,
                                size: 16,
                                color: Color(0xFF1565C0),
                              ),
                              const SizedBox(width: 6),
                              Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  const Text(
                                    'Distance',
                                    style: TextStyle(
                                      fontSize: 11,
                                      color: Color(0xFF9E9E9E),
                                    ),
                                  ),
                                  Text(
                                    _walkTime,
                                    style: const TextStyle(
                                      fontSize: 16,
                                      fontWeight: FontWeight.w700,
                                      color: Color(0xFF1A1A2E),
                                    ),
                                  ),
                                ],
                              ),
                            ],
                          ),
                          const SizedBox(height: 14),

                          // Crowd level
                          Row(
                            children: [
                              const Icon(
                                Icons.people_outline,
                                size: 16,
                                color: Color(0xFF9E9E9E),
                              ),
                              const SizedBox(width: 6),
                              const Text(
                                'Crowd Level',
                                style: TextStyle(
                                  fontSize: 12,
                                  color: Color(0xFF9E9E9E),
                                ),
                              ),
                              const Spacer(),
                              Text(
                                _crowdLevel,
                                style: const TextStyle(
                                  fontSize: 12,
                                  fontWeight: FontWeight.w600,
                                  color: Color(0xFF424242),
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 8),
                          ClipRRect(
                            borderRadius: BorderRadius.circular(4),
                            child: LinearProgressIndicator(
                              value: _crowdFill,
                              minHeight: 7,
                              backgroundColor: const Color(0xFFEEEEEE),
                              valueColor: AlwaysStoppedAnimation<Color>(
                                _crowdBarColor,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),

                    const SizedBox(height: 14),

                    // Start Navigation button
                    SizedBox(
                      width: double.infinity,
                      height: 54,
                      child: ElevatedButton.icon(
                        onPressed: () {},
                        icon: const Icon(
                          Icons.near_me,
                          size: 20,
                          color: Colors.white,
                        ),
                        label: const Text(
                          'Start Navigation',
                          style: TextStyle(
                            fontSize: 17,
                            fontWeight: FontWeight.w700,
                            color: Colors.white,
                          ),
                        ),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: const Color(0xFF1565C0),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(14),
                          ),
                          elevation: 0,
                        ),
                      ),
                    ),

                    const SizedBox(height: 10),

                    // Alternatives + info row
                    Row(
                      children: [
                        Expanded(
                          child: SizedBox(
                            height: 48,
                            child: OutlinedButton.icon(
                              onPressed: _showAlternatives,
                              icon: const Icon(
                                Icons.menu,
                                size: 17,
                                color: Color(0xFF424242),
                              ),
                              label: const Text(
                                'Alternatives',
                                style: TextStyle(
                                  fontSize: 14,
                                  fontWeight: FontWeight.w600,
                                  color: Color(0xFF424242),
                                ),
                              ),
                              style: OutlinedButton.styleFrom(
                                side: const BorderSide(
                                  color: Color(0xFFE0E0E0),
                                ),
                                backgroundColor: Colors.white,
                                shape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(12),
                                ),
                              ),
                            ),
                          ),
                        ),
                        const SizedBox(width: 10),
                        Container(
                          width: 48,
                          height: 48,
                          decoration: BoxDecoration(
                            color: Colors.white,
                            borderRadius: BorderRadius.circular(12),
                            border: Border.all(color: const Color(0xFFE0E0E0)),
                          ),
                          child: const Icon(
                            Icons.info_outline,
                            size: 20,
                            color: Color(0xFF424242),
                          ),
                        ),
                      ],
                    ),

                    const SizedBox(height: 12),

                    // Footer
                    Text(
                      'Updated $_lastUpdated',
                      style: const TextStyle(
                        fontSize: 11,
                        color: Color(0xFF9E9E9E),
                      ),
                    ),
                    const SizedBox(height: 16),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _LegendLine extends StatelessWidget {
  final Color color;
  final bool dashed;
  const _LegendLine({required this.color, required this.dashed});

  @override
  Widget build(BuildContext context) {
    return CustomPaint(
      size: const Size(24, 2),
      painter: _LinePainter(color: color, dashed: dashed),
    );
  }
}

class _LinePainter extends CustomPainter {
  final Color color;
  final bool dashed;
  const _LinePainter({required this.color, required this.dashed});

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = color
      ..strokeWidth = 2
      ..style = PaintingStyle.stroke;
    if (!dashed) {
      canvas.drawLine(
        Offset(0, size.height / 2),
        Offset(size.width, size.height / 2),
        paint,
      );
    } else {
      double x = 0;
      while (x < size.width) {
        canvas.drawLine(
          Offset(x, size.height / 2),
          Offset((x + 4).clamp(0, size.width), size.height / 2),
          paint,
        );
        x += 7;
      }
    }
  }

  @override
  bool shouldRepaint(_LinePainter old) => false;
}
