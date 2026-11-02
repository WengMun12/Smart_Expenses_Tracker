import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

import '../config.dart';

class AddExpensePage extends StatefulWidget {
  final String token;
  const AddExpensePage({super.key, required this.token});

  @override
  State<AddExpensePage> createState() => _AddExpensePageState();
}

class _AddExpensePageState extends State<AddExpensePage> {
  final _amount = TextEditingController();
  final _description = TextEditingController();
  final _aiText = TextEditingController();
  bool _aiLoading = false;
  DateTime _date = DateTime.now();
  List<dynamic> _category = [];
  int? _categoryId;
  bool _saving = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadCategory();
  }

  Future<void> _loadCategory() async {
    try {
      final res = await http.get(Uri.parse('$baseUrl/category'));
      if (res.statusCode == 200) {
        setState(() => _category = jsonDecode(res.body));
      }
    } catch (e) {
      setState(() => _error = 'Could not lead category');
    }
  }

  Future<void> _pickDate() async {
    final picked = await showDatePicker(
      context: context,
      initialDate: _date,
      firstDate: DateTime(2020),
      lastDate: DateTime(2100),
    );
    if (picked != null) setState(() => _date = picked);
  }

  String get _dateText =>
      '${_date.year}-${_date.month.toString().padLeft(2, '0')}-${_date.day.toString().padLeft(2, '0')}';

  Future<void> _save() async {
    final amount = double.tryParse(_amount.text.trim());
    if (amount == null || _categoryId == null) {
      setState(() => _error = 'Enter a valid amount and pick a category');
      return;
    }
    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      final res = await http.post(
        Uri.parse('$baseUrl/expenses'),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer ${widget.token}',
        },
        body: jsonEncode({
          'amount': amount,
          'description': _description.text.trim(),
          'date': _dateText,
          'categoryID': _categoryId,
        }),
      );
      if (res.statusCode == 200) {
        if (!mounted) return;
        Navigator.pop(context, true);
        return;
      }
      setState(() => _error = 'Failed to save (${res.statusCode})');
    } catch (e) {
      setState(() => _error = 'Error: $e');
    }
    if (mounted) setState(() => _saving = false);
  }

  Future<void> _autoFill() async {
    final text = _aiText.text.trim();
    if (text.isEmpty) return;
    setState(() {
      _aiLoading = true;
      _error = null;
    });
    try {
      final res = await http
          .post(
            Uri.parse('$baseUrl/ai/categorize'),
            headers: {
              'Content-Type': 'application/json',
              'Authorization': 'Bearer ${widget.token}',
            },
            body: jsonEncode({'text': text}),
          )
          .timeout(const Duration(seconds: 30));
      if (res.statusCode == 200) {
        final data = jsonDecode(res.body);
        setState(() {
          _amount.text = '${data['amount'] ?? ''}';
          _description.text = data['description'] ?? '';
          _categoryId = data['categoryID'];
        });
      } else {
        setState(() => _error = 'AI could not read that (${res.statusCode})');
      }
    } catch (e) {
      setState(() => _error = 'Error: $e');
    }
    if (mounted) setState(() => _aiLoading = false);
  }

  @override
  void dispose() {
    _amount.dispose();
    _description.dispose();
    _aiText.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Add Expense')),
      body: ListView(
        padding: const EdgeInsets.all(24),
        children: [
          TextField(
            controller: _aiText,
            decoration: const InputDecoration(
              labelText: 'Describe it (e.g. Grab to campus RM12)',
              prefixIcon: Icon(Icons.auto_awesome),
            ),
          ),
          const SizedBox(height: 8),
          OutlinedButton.icon(
            onPressed: _aiLoading ? null : _autoFill,
            icon: _aiLoading
                ? const SizedBox(
                    height: 16,
                    width: 16,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.auto_awesome),
            label: const Text('Auto-fill with AI'),
          ),
          const Divider(height: 32),
          TextField(
            controller: _amount,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            decoration: const InputDecoration(labelText: 'Amount (RM)'),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _description,
            decoration: const InputDecoration(labelText: 'Description'),
          ),
          const SizedBox(height: 12),
          DropdownButtonFormField<int>(
            initialValue: _categoryId,
            decoration: const InputDecoration(labelText: 'Category'),
            items: _category
                .map(
                  (c) => DropdownMenuItem<int>(
                    value: c['categoryID'],
                    child: Text(c['categoryName']),
                  ),
                )
                .toList(),
            onChanged: (v) => setState(() => _categoryId = v),
          ),
          const SizedBox(height: 12),
          ListTile(
            contentPadding: EdgeInsets.zero,
            title: Text('Date: $_dateText'),
            trailing: const Icon(Icons.calendar_today),
            onTap: _pickDate,
          ),
          if (_error != null)
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Text(_error!, style: const TextStyle(color: Colors.red)),
            ),
          const SizedBox(height: 16),
          ElevatedButton(
            onPressed: _saving ? null : _save,
            child: _saving
                ? const SizedBox(
                    height: 18,
                    width: 18,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Text('Save'),
          ),
        ],
      ),
    );
  }
}
