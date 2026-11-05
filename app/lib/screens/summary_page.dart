import 'dart:convert';
import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import '../config.dart';

class SummaryPage extends StatefulWidget {
  final String token;
  const SummaryPage({super.key, required this.token});

  @override
  State<SummaryPage> createState() => _SummaryPageState();
}

class _SummaryPageState extends State<SummaryPage> {
  DateTime _month = DateTime(DateTime.now().year, DateTime.now().month);
  double _total = 0;
  List<dynamic> _items = [];
  bool _loading = true;
  String? _error;
  List<String> _tips = [];
  bool _tipsLoading = false;
  String? _tipsError;

  static const _colors = [
    Colors.deepPurple, Colors.orange, Colors.teal,
    Colors.pink, Colors.blue, Colors.green, Colors.brown,
  ];

  String get _monthText =>
      '${_month.year}-${_month.month.toString().padLeft(2, '0')}';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final res = await http.get(
        Uri.parse('$baseUrl/summary?month=$_monthText'),
        headers: {'Authorization': 'Bearer ${widget.token}'},
      ).timeout(const Duration(seconds: 15));
      if (res.statusCode == 200) {
        final data = jsonDecode(res.body);
        _total = (data['total'] as num).toDouble();
        _items = data['by_category'];
      } else {
        _error = 'Failed to load (${res.statusCode}';
      }
    } catch (e) {
      _error = 'Error: $e';
    }
    if (mounted) setState(() => _loading = false);
  }

  Future<void> _getTips() async {
    setState(() {
      _tipsLoading = true;
      _tipsError = null;
    });
    try {
      final res = await http.post(
        Uri.parse('$baseUrl/ai/tips?months=$_monthText'),
        headers: {'Authorization': 'Bearer ${widget.token}'},
      ).timeout(const Duration(seconds: 60));
      if (res.statusCode == 200) {
        _tips = List<String>.from(jsonDecode(res.body)['tips']);
      } else {
        _tipsError = 'AI is busy right now. Please try again in a minute.';
      }
    } catch (e) {
      _tipsError = 'Error: $e';
    }
    if (mounted) setState(() => _tipsLoading = false);
  }

  void _changeMonth(int delta) {
    setState(() {
      _month = DateTime(_month.year, _month.month + delta);
      _tips = [];
      _tipsError = null;
    });
    _load();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Spending Summary')),
      body: Column(
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              IconButton(
                icon: const Icon(Icons.chevron_left),
                onPressed: () => _changeMonth(-1)),
              Text(_monthText, style: const TextStyle(fontSize: 18)),
              IconButton(
                icon: const Icon(Icons.chevron_right),
                onPressed: () => _changeMonth(1)),
            ],
          ),
          Expanded(child: _buildContent()),
        ],
      ),
    );
  }

  Widget _buildContent() {
    if (_loading) return const Center(child: CircularProgressIndicator());
    if (_error != null) return Center(child: Text(_error!));
    if (_items.isEmpty) return const Center(child: Text('No expenses this month'));

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Center(
          child: Text('Total: RM ${_total.toStringAsFixed(2)}',
              style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold)),
        ),
        const SizedBox(height: 16),
        SizedBox(
          height: 240,
          child: PieChart(
            PieChartData(
              sectionsSpace: 2,
              centerSpaceRadius: 40,
              sections: [
                for (var i = 0; i < _items.length; i++)
                  PieChartSectionData(
                    value: (_items[i]['total'] as num).toDouble(),
                    color: _colors[i % _colors.length],
                    radius: 70,
                    title: _total == 0
                        ? ''
                        : '${((_items[i]['total'] as num) / _total * 100).round()}%',
                    titleStyle: const TextStyle(
                      color: Colors.white, fontWeight: FontWeight.bold),
                  ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 16),
        for (var i = 0; i < _items.length; i++)
          ListTile(
            leading: CircleAvatar(
              radius: 8, backgroundColor: _colors[i % _colors.length]),
            title: Text(_items[i]['category']),
            trailing: Text(
              'RM ${(_items[i]['total'] as num).toStringAsFixed(2)}'),
          ),
        const Divider(height: 32),
        OutlinedButton.icon(
            onPressed: _tipsLoading ? null : _getTips,
            icon: _tipsLoading
                ? const SizedBox(
                   height: 16,
                   width: 16,
                   child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.auto_awesome),
            label: const Text('Get AI saving tips')
        ),
        if (_tipsError != null)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Text(_tipsError!, style: const TextStyle(color: Colors.red)),
          ),
        if (_tips.isNotEmpty)
          Card(
            margin: const EdgeInsets.only(top: 12),
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Saving tips', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                  const SizedBox(height: 8),
                  for (final t in _tips)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 8),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Icon(Icons.lightbulb_outline, size: 18),
                          const SizedBox(width: 8),
                          Expanded(child: Text(t)),
                        ],
                      ),
                    ),
                  const Text(
                    'AI-generated suggestions, not financial advice.',
                    style: TextStyle(fontSize: 11, color: Colors.grey),
                  ),
                ],
              ),
            ),
          ),
      ],
    );
  }
}