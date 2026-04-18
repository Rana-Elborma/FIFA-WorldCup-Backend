import 'package:flutter/material.dart';

/// Which gate to highlight with a solid blue route line
enum PreviewGate { gate1, gate2, gate3, gate4 }

class StadiumMap extends StatelessWidget {
  final PreviewGate activeGate;
  const StadiumMap({super.key, this.activeGate = PreviewGate.gate2});

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        color: Color(0xFFEFF4FB),
      ),
      child: Stack(
        children: [
          // Painted map
          Positioned.fill(
            child: CustomPaint(painter: _MapPainter(activeGate: activeGate)),
          ),
          // Navigation button
          Positioned(
            right: 16,
            bottom: 16,
            child: Container(
              width: 40,
              height: 40,
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(20),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withOpacity(0.12),
                    blurRadius: 6,
                    offset: const Offset(0, 2),
                  ),
                ],
              ),
              child: const Icon(Icons.near_me_outlined, size: 20, color: Color(0xFF424242)),
            ),
          ),
        ],
      ),
    );
  }
}

class _MapPainter extends CustomPainter {
  final PreviewGate activeGate;
  const _MapPainter({required this.activeGate});

  @override
  void paint(Canvas canvas, Size size) {
    final w = size.width;
    final h = size.height;

    // ── User location dot (bottom-left area)
    final userPos = Offset(w * 0.12, h * 0.72);

    // ── Stadium oval (dashed)
    final ovalRect = Rect.fromCenter(
      center: Offset(w * 0.58, h * 0.46),
      width: w * 0.72,
      height: h * 0.58,
    );
    _drawDashedOval(canvas, ovalRect);

    // ── Gate positions
    final gates = {
      PreviewGate.gate1: Offset(w * 0.73, h * 0.16),
      PreviewGate.gate2: Offset(w * 0.30, h * 0.22),
      PreviewGate.gate3: Offset(w * 0.75, h * 0.50),
      PreviewGate.gate4: Offset(w * 0.30, h * 0.40),
    };

    // ── Dashed alternative routes (grey) to all non-active gates
    final dashPaint = Paint()
      ..color = const Color(0xFFAAAAAA)
      ..strokeWidth = 1.5
      ..style = PaintingStyle.stroke;

    for (final entry in gates.entries) {
      if (entry.key != activeGate) {
        _drawDashedLine(canvas, userPos, entry.value, dashPaint);
      }
    }

    // ── Solid recommended route (blue) to active gate
    final routePaint = Paint()
      ..color = const Color(0xFF1565C0)
      ..strokeWidth = 2.5
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;
    canvas.drawLine(userPos, gates[activeGate]!, routePaint);

    // ── Gate dots + labels
    for (final entry in gates.entries) {
      final isActive = entry.key == activeGate;
      final dotPaint = Paint()
        ..color = isActive ? const Color(0xFF1565C0) : const Color(0xFF9E9E9E)
        ..style = PaintingStyle.fill;
      canvas.drawCircle(entry.value, isActive ? 5 : 3.5, dotPaint);

      final label = _gateName(entry.key);
      final tp = TextPainter(
        text: TextSpan(
          text: label,
          style: TextStyle(
            fontSize: 11,
            fontWeight: isActive ? FontWeight.w700 : FontWeight.w400,
            color: isActive ? const Color(0xFF1565C0) : const Color(0xFF616161),
          ),
        ),
        textDirection: TextDirection.ltr,
      )..layout();
      tp.paint(canvas, entry.value + const Offset(7, -8));
    }

    // ── User blue circle
    final userBgPaint = Paint()
      ..color = const Color(0xFF1565C0).withOpacity(0.15)
      ..style = PaintingStyle.fill;
    canvas.drawCircle(userPos, 14, userBgPaint);
    final userDotPaint = Paint()
      ..color = const Color(0xFF1565C0)
      ..style = PaintingStyle.fill;
    canvas.drawCircle(userPos, 7, userDotPaint);
    final userRingPaint = Paint()
      ..color = Colors.white
      ..strokeWidth = 2
      ..style = PaintingStyle.stroke;
    canvas.drawCircle(userPos, 7, userRingPaint);
  }

  String _gateName(PreviewGate g) {
    switch (g) {
      case PreviewGate.gate1:
        return 'Gate 1';
      case PreviewGate.gate2:
        return 'Gate 2';
      case PreviewGate.gate3:
        return 'Gate 3';
      case PreviewGate.gate4:
        return 'Gate 4';
    }
  }

  void _drawDashedOval(Canvas canvas, Rect rect) {
    final path = Path()..addOval(rect);
    final dashPaint = Paint()
      ..color = const Color(0xFFB0BEC5)
      ..strokeWidth = 1.5
      ..style = PaintingStyle.stroke;
    _drawDashedPath(canvas, path, dashPaint, dashLen: 8, gapLen: 5);
  }

  void _drawDashedLine(Canvas canvas, Offset p1, Offset p2, Paint paint) {
    final dx = p2.dx - p1.dx;
    final dy = p2.dy - p1.dy;
    final dist = (p2 - p1).distance;
    const dash = 6.0;
    const gap = 4.0;
    double drawn = 0;
    while (drawn < dist) {
      final start = drawn / dist;
      final end = ((drawn + dash) / dist).clamp(0.0, 1.0);
      canvas.drawLine(
        Offset(p1.dx + dx * start, p1.dy + dy * start),
        Offset(p1.dx + dx * end, p1.dy + dy * end),
        paint,
      );
      drawn += dash + gap;
    }
  }

  void _drawDashedPath(Canvas canvas, Path path, Paint paint,
      {double dashLen = 10, double gapLen = 5}) {
    final metrics = path.computeMetrics();
    for (final metric in metrics) {
      double dist = 0;
      while (dist < metric.length) {
        final end = (dist + dashLen).clamp(0.0, metric.length);
        canvas.drawPath(metric.extractPath(dist, end), paint);
        dist += dashLen + gapLen;
      }
    }
  }

  @override
  bool shouldRepaint(_MapPainter old) => old.activeGate != activeGate;
}
