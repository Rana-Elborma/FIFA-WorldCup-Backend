import 'package:flutter/material.dart';

class CrowdBadge extends StatelessWidget {
  final String severity;
  const CrowdBadge({super.key, required this.severity});

  Color get _bg {
    switch (severity) {
      case 'HIGH':
        return const Color(0xFFFFE5E5);
      case 'MEDIUM':
        return const Color(0xFFFFF3E0);
      default:
        return const Color(0xFFE8F5E9);
    }
  }

  Color get _fg {
    switch (severity) {
      case 'HIGH':
        return const Color(0xFFC62828);
      case 'MEDIUM':
        return const Color(0xFFE65100);
      default:
        return const Color(0xFF2E7D32);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: _bg,
        borderRadius: BorderRadius.circular(20),
      ),
      child: Text(
        severity,
        style: TextStyle(
          fontSize: 12,
          fontWeight: FontWeight.w700,
          color: _fg,
        ),
      ),
    );
  }
}
