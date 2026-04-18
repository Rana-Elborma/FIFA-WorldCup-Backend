import 'package:geolocator/geolocator.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'gate_coordinates.dart';

class LocationService {
  static Position? _lastPosition;
  static Position? get lastPosition => _lastPosition;

  /// Requests permission and returns the current GPS position.
  /// Returns null if permission denied or GPS unavailable.
  static Future<Position?> getCurrentPosition() async {
    try {
      bool serviceEnabled = await Geolocator.isLocationServiceEnabled();
      if (!serviceEnabled) return null;

      LocationPermission permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied) {
        permission = await Geolocator.requestPermission();
        if (permission == LocationPermission.denied) return null;
      }
      if (permission == LocationPermission.deniedForever) return null;

      final pos = await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(
          accuracy: LocationAccuracy.high,
          timeLimit: Duration(seconds: 10),
        ),
      );
      _lastPosition = pos;
      return pos;
    } catch (_) {
      return null;
    }
  }

  /// Returns distance in meters from [pos] to a gate coordinate.
  static double distanceTo(Position pos, GateCoord gate) {
    return Geolocator.distanceBetween(
      pos.latitude, pos.longitude,
      gate.lat,    gate.lon,
    );
  }

  /// Walk time in minutes based on real distance (average 80 m/min walking).
  static int walkMinutes(double distanceMeters) =>
      (distanceMeters / 80).ceil().clamp(1, 60);

  /// Picks the best gate using GPS distance + crowd level.
  /// Score = 40% distance weight + 60% crowd weight (lower = better).
  static GateCoord bestGate(Position pos, String riskLevel) {
    const crowdScore = {'Normal': 0.2, 'Busy': 0.6, 'Critical': 1.0};
    final risk = crowdScore[riskLevel] ?? 0.2;

    // Calculate distances
    final distances = {
      for (final g in kGateCoords) g.id: distanceTo(pos, g)
    };
    final maxDist = distances.values.reduce((a, b) => a > b ? a : b);

    GateCoord? best;
    double bestScore = double.infinity;

    for (final gate in kGateCoords) {
      final normDist = maxDist > 0 ? distances[gate.id]! / maxDist : 0.0;
      // Gates 3 and 1 are busier by design — add small crowd offset per gate
      final gateOffset = gate.id == 3 ? 0.3 : gate.id == 1 ? 0.1 : 0.0;
      final score = 0.4 * normDist + 0.6 * (risk + gateOffset).clamp(0, 1);
      if (score < bestScore) {
        bestScore = score;
        best = gate;
      }
    }
    return best ?? kGateCoords[2]; // default Gate 3
  }

  /// Sends encrypted GPS to Supabase via the secure RPC function.
  /// Raw coordinates never leave the database unencrypted.
  static Future<void> saveGpsToSupabase(
    Position pos, {
    required int stadiumId,
    required int zoneId,
    required int nearestGateId,
    required String sessionId,
  }) async {
    try {
      await Supabase.instance.client.rpc('insert_gps_event', params: {
        'p_latitude':        pos.latitude,
        'p_longitude':       pos.longitude,
        'p_stadium_id':      stadiumId,
        'p_zone_id':         zoneId,
        'p_nearest_gate_id': nearestGateId,
        'p_session_id':      sessionId,
      });
    } catch (_) {
      // GPS save failure is non-fatal — app continues working
    }
  }
}
