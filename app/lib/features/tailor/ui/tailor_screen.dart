import 'dart:convert';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../services/tailor_service.dart';

class TailorScreen extends StatefulWidget {
  const TailorScreen({super.key});

  @override
  State<TailorScreen> createState() => _TailorScreenState();
}

class _TailorScreenState extends State<TailorScreen> {
  final _jdController = TextEditingController();
  final _roleController = TextEditingController();
  final _companyController = TextEditingController();
  final _service = TailorService();

  bool _busy = false;
  String? _error;
  Map<String, dynamic>? _result;

  @override
  void dispose() {
    _jdController.dispose();
    _roleController.dispose();
    _companyController.dispose();
    super.dispose();
  }

  Future<void> _runTailor() async {
    final jd = _jdController.text.trim();
    if (jd.isEmpty) {
      setState(() => _error = 'Paste a job description first.');
      return;
    }

    setState(() {
      _busy = true;
      _error = null;
      _result = null;
    });

    try {
      final data = await _service.tailor(
        jobDescription: jd,
        targetRole: _roleController.text,
        company: _companyController.text,
      );
      if (!mounted) return;
      setState(() {
        _result = data;
        _busy = false;
      });
    } on DioException catch (error) {
      if (!mounted) return;
      final detail = error.response?.data;
      final message = detail is Map && detail['detail'] != null
          ? detail['detail'].toString()
          : (error.message ?? 'Tailor request failed');
      setState(() {
        _error = message;
        _busy = false;
      });
    } on Object catch (error) {
      if (!mounted) return;
      setState(() {
        _error = '$error';
        _busy = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final resume = _result?['resume'];
    final stub = _result?['stub'] == true;
    final detail = _result?['detail'] as String?;

    return Scaffold(
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(24),
          children: [
            Row(
              children: [
                IconButton(
                  onPressed: () => context.go('/'),
                  icon: const Icon(Icons.arrow_back),
                ),
                Expanded(
                  child: Text(
                    'Tailor resume',
                    style: theme.textTheme.headlineSmall,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              'Paste a job description. We retrieve matching pieces of your '
              'remade profile and rewrite a tailored resume.',
              style: theme.textTheme.bodyMedium,
            ),
            const SizedBox(height: 20),
            TextField(
              controller: _jdController,
              minLines: 8,
              maxLines: 14,
              decoration: const InputDecoration(
                labelText: 'Job description',
                alignLabelWithHint: true,
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _roleController,
              decoration: const InputDecoration(
                labelText: 'Target role (optional)',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _companyController,
              decoration: const InputDecoration(
                labelText: 'Company (optional)',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 16),
            FilledButton(
              onPressed: _busy ? null : _runTailor,
              child: _busy
                  ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Text('Generate tailored resume'),
            ),
            if (_error != null) ...[
              const SizedBox(height: 16),
              Text(_error!, style: TextStyle(color: theme.colorScheme.error)),
            ],
            if (_result != null) ...[
              const SizedBox(height: 24),
              if (detail != null)
                Text(detail, style: theme.textTheme.bodySmall),
              if (stub)
                Padding(
                  padding: const EdgeInsets.only(top: 8),
                  child: Text(
                    'Stub response (OpenRouter not configured).',
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: theme.colorScheme.tertiary,
                    ),
                  ),
                ),
              const SizedBox(height: 12),
              SelectableText(
                const JsonEncoder.withIndent('  ').convert(resume ?? _result),
                style: theme.textTheme.bodySmall?.copyWith(
                  fontFamily: 'monospace',
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
