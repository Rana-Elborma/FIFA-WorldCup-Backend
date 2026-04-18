import 'package:flutter/material.dart';

class GateCard extends StatelessWidget {
  final String gateName;
  final int waitMin;
  final int walkMin;
  final String crowd; // Low / Medium / High
  final bool isRecommended;
  final bool isSelected;
  final int? distanceM;
  final String? note;
  final VoidCallback? onTap;

  const GateCard({
    super.key,
    required this.gateName,
    required this.waitMin,
    required this.walkMin,
    required this.crowd,
    this.isRecommended = false,
    this.isSelected = false,
    this.distanceM,
    this.note,
    this.onTap,
  });

  Color get _barColor {
    switch (crowd) {
      case 'High':
        return const Color(0xFFE53935);
      case 'Medium':
        return const Color(0xFFFFA726);
      default:
        return const Color(0xFF43A047);
    }
  }

  double get _barFill {
    switch (crowd) {
      case 'High':
        return 0.85;
      case 'Medium':
        return 0.55;
      default:
        return 0.25;
    }
  }

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        margin: const EdgeInsets.only(bottom: 12),
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(
            color: isSelected ? const Color(0xFF1565C0) : const Color(0xFFE0E0E0),
            width: isSelected ? 2 : 1,
          ),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.04),
              blurRadius: 8,
              offset: const Offset(0, 2),
            ),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Gate name row
            Row(
              children: [
                Text(
                  gateName,
                  style: const TextStyle(
                    fontSize: 17,
                    fontWeight: FontWeight.w700,
                    color: Color(0xFF1A1A2E),
                  ),
                ),
                if (isRecommended) ...[
                  const SizedBox(width: 8),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                    decoration: BoxDecoration(
                      color: const Color(0xFF1976D2),
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: const [
                        Icon(Icons.check, size: 10, color: Colors.white),
                        SizedBox(width: 3),
                        Text(
                          'Recommended',
                          style: TextStyle(
                            fontSize: 11,
                            color: Colors.white,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
                const Spacer(),
                // Radio
                Container(
                  width: 22,
                  height: 22,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    border: Border.all(
                      color: isSelected ? const Color(0xFF1565C0) : const Color(0xFFBDBDBD),
                      width: 2,
                    ),
                  ),
                  child: isSelected
                      ? Center(
                          child: Container(
                            width: 12,
                            height: 12,
                            decoration: const BoxDecoration(
                              shape: BoxShape.circle,
                              color: Color(0xFF1565C0),
                            ),
                          ),
                        )
                      : null,
                ),
              ],
            ),
            if (note != null) ...[
              const SizedBox(height: 4),
              Row(
                children: [
                  const Icon(Icons.check, size: 13, color: Color(0xFF43A047)),
                  const SizedBox(width: 4),
                  Text(
                    note!,
                    style: const TextStyle(fontSize: 12, color: Color(0xFF43A047)),
                  ),
                ],
              ),
            ],
            const SizedBox(height: 14),
            // Stats row
            Row(
              children: [
                _StatItem(icon: Icons.access_time_rounded, label: 'Wait', value: '$waitMin min'),
                const SizedBox(width: 20),
                _StatItem(icon: Icons.near_me_outlined, label: 'Walk', value: '$walkMin min'),
                const SizedBox(width: 20),
                _StatItem(icon: Icons.people_outline, label: 'Crowd', value: crowd),
              ],
            ),
            const SizedBox(height: 10),
            // Crowd bar
            ClipRRect(
              borderRadius: BorderRadius.circular(4),
              child: LinearProgressIndicator(
                value: _barFill,
                minHeight: 6,
                backgroundColor: const Color(0xFFEEEEEE),
                valueColor: AlwaysStoppedAnimation<Color>(_barColor),
              ),
            ),
            if (distanceM != null) ...[
              const SizedBox(height: 8),
              Text(
                '$distanceM m distance',
                style: const TextStyle(fontSize: 12, color: Color(0xFF9E9E9E)),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _StatItem extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;
  const _StatItem({required this.icon, required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Icon(icon, size: 15, color: const Color(0xFF9E9E9E)),
        const SizedBox(width: 4),
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(label, style: const TextStyle(fontSize: 10, color: Color(0xFF9E9E9E))),
            Text(value,
                style: const TextStyle(
                    fontSize: 13, fontWeight: FontWeight.w600, color: Color(0xFF1A1A2E))),
          ],
        ),
      ],
    );
  }
}
