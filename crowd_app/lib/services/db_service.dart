import 'package:supabase_flutter/supabase_flutter.dart';
import '../models/prediction.dart';

class DbService {
  final _db = Supabase.instance.client;

  Future<List<GatePrediction>> fetchPredictions() async {
    final res = await _db
        .from('prediction')
        .select('*, gate(name)')
        .order('ts', ascending: false)
        .limit(4);
    return (res as List)
        .map((m) => GatePrediction.fromMap(m as Map<String, dynamic>))
        .toList();
  }
}
