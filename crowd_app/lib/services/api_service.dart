import 'dart:convert';
import 'package:http/http.dart' as http;

// Change this to your computer's local IP when running on a real phone.
// e.g. 'http://192.168.1.5:8000'
// For Flutter Web (running in browser) keep as localhost.
const String _base = 'http://localhost:8000';

class ApiService {
  static Future<Map<String, dynamic>?> fetchMetrics() async {
    try {
      final res = await http
          .get(Uri.parse('$_base/api/v1/metrics/latest'))
          .timeout(const Duration(seconds: 5));
      if (res.statusCode == 200) {
        return jsonDecode(res.body) as Map<String, dynamic>;
      }
    } catch (_) {}
    return null;
  }

  static Future<Map<String, dynamic>?> fetchForecast() async {
    try {
      final res = await http
          .get(Uri.parse('$_base/api/v1/predictions/15min'))
          .timeout(const Duration(seconds: 5));
      if (res.statusCode == 200) {
        return jsonDecode(res.body) as Map<String, dynamic>;
      }
    } catch (_) {}
    return null;
  }
}

// Converts backend riskLevel string → crowd label and bar fill value.
String crowdLabelFromRisk(String risk) {
  switch (risk) {
    case 'Critical':
      return 'High';
    case 'Busy':
      return 'Medium';
    default:
      return 'Low';
  }
}

double crowdFillFromRisk(String risk) {
  switch (risk) {
    case 'Critical':
      return 0.85;
    case 'Busy':
      return 0.55;
    default:
      return 0.20;
  }
}

// Estimates wait minutes from person count.
int waitMinFromCount(int count) => (count / 10).ceil().clamp(1, 60);
