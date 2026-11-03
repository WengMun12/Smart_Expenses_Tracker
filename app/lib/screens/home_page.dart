import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

import '../../config.dart';
import 'add_expense_page.dart';

class HomePage extends StatefulWidget {
  final String token;
  const HomePage({super.key, required this.token});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  List<dynamic> _expenses = [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadExpenses();
  }

  Future<void> _loadExpenses() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final res = await http.get(
        Uri.parse('$baseUrl/expenses'),
        headers: {'Authorization': 'Bearer ${widget.token}'},
      );
      if (res.statusCode == 200) {
        _expenses = jsonDecode(res.body);
      } else {
        _error = 'Failed to load (${res.statusCode})';
      }
    } catch (e) {
      _error = 'Error: $e';
    }
    if (mounted) setState(() => _loading = false);
  }

  Future<void> _deleteExpense(int id) async {
    try {
      final res = await http.delete(
        Uri.parse('$baseUrl/expenses/$id'),
        headers: {'Authorization': 'Bearer ${widget.token}'},
      );
      if (res.statusCode != 200 && mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Delete failed (${res.statusCode}')),
        );
        _loadExpenses();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text('Error: $e')));
        _loadExpenses();
      }
    }
  }

  IconData _categoryIcon(String? name) {
    switch (name) {
      case 'Food':
        return Icons.restaurant;
      case 'Transport':
        return Icons.directions_car;
      case 'Shopping':
        return Icons.shopping_bag;
      case 'Savings':
        return Icons.savings;
      default:
        return Icons.category;
    }
  }

  Widget _buildBody() {
    if (_loading) return const Center(child: CircularProgressIndicator());
    if (_error != null) return Center(child: Text(_error!));
    if (_expenses.isEmpty) return const Center(child: Text('No expenses yet'));

    return RefreshIndicator(
      onRefresh: _loadExpenses,
      child: ListView.builder(
        itemCount: _expenses.length,
        itemBuilder: (context, i) {
          final e = _expenses[i];
          return Dismissible(
            key: ValueKey(e['expensesID']),
            direction: DismissDirection.endToStart,
            confirmDismiss: (direction) async {
              return await showDialog<bool>(
                context: context,
                builder: (ctx) => AlertDialog(
                  title: const Text('Delete expense?'),
                  content: Text(
                    'Delete "${e['description'] ?? 'this expense'}" (RM ${e['amount']})?',
                  ),
                  actions: [
                    TextButton(
                      onPressed: () => Navigator.pop(ctx, false),
                      child: const Text('Cancel'),
                    ),
                    TextButton(
                      onPressed: () => Navigator.pop(ctx, true),
                      child: const Text('Delete', style: TextStyle(color: Colors.red),),
                    ),
                  ],
                ),
              );
            },
            background: Container(
              color: Colors.red,
              alignment: Alignment.centerRight,
              padding: const EdgeInsets.only(right: 20),
              child: const Icon(Icons.delete, color: Colors.white),
            ),
            onDismissed: (_) {
              final id = e['expensesID'];
              setState(() => _expenses.removeAt(i));
              _deleteExpense(id);
            },
            child: ListTile(
              leading: CircleAvatar(
                child: Icon(_categoryIcon(e['categoryName'])),
              ),
              title: Text(e['description'] ?? '(no description)'),
              subtitle: Text('${e['categoryName'] ?? 'Uncategorized'} • ${e['sdate']}'),
              trailing: Text('RM ${e['amount']}'),
            ),
          );
        },
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('My Expenses')),
      body: _buildBody(),
      floatingActionButton: FloatingActionButton(
        onPressed: () async {
          final added = await Navigator.push(
            context,
            MaterialPageRoute(
              builder: (_) => AddExpensePage(token: widget.token),
            ),
          );
          if (added == true) _loadExpenses();
        },
        child: const Icon(Icons.add),
      ),
    );
  }
}
