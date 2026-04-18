// Real-world GPS coordinates for each gate at Aramco Stadium, Dhahran.
// Used to calculate how far the user is from each gate.
class GateCoord {
  final int id;
  final String name;
  final double lat;
  final double lon;
  final int walkMinBase; // baseline walk time at 80m/min

  const GateCoord({
    required this.id,
    required this.name,
    required this.lat,
    required this.lon,
    required this.walkMinBase,
  });
}

const List<GateCoord> kGateCoords = [
  GateCoord(id: 1, name: 'Gate 1', lat: 26.3065, lon: 50.1517, walkMinBase: 7),
  GateCoord(id: 2, name: 'Gate 2', lat: 26.3031, lon: 50.1525, walkMinBase: 5),
  GateCoord(id: 3, name: 'Gate 3', lat: 26.3048, lon: 50.1540, walkMinBase: 6),
  GateCoord(id: 4, name: 'Gate 4', lat: 26.3048, lon: 50.1494, walkMinBase: 7),
];
