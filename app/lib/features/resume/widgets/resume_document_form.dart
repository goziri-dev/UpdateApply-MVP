import 'package:flutter/material.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_theme.dart';

/// Shared in-place editor for a `ResumeDocument` map.
///
/// Mirrors onboarding Review field patterns (outlined fields, section titles)
/// with education + editable skills for post-onboarding hybrid edit.
/// Supports Add / Remove rows and optional deepen (guided or journal) per item.
class ResumeDocumentForm extends StatefulWidget {
  const ResumeDocumentForm({
    super.key,
    required this.initialDocument,
    this.enableDeepen = false,
    this.onDeepenExperience,
    this.onDeepenProject,
  });

  final Map<String, dynamic> initialDocument;

  /// When true, shows Deepen on experience/project rows (master).
  final bool enableDeepen;

  final void Function(int index)? onDeepenExperience;
  final void Function(int index)? onDeepenProject;

  @override
  State<ResumeDocumentForm> createState() => ResumeDocumentFormState();
}

class ResumeDocumentFormState extends State<ResumeDocumentForm> {
  final _name = TextEditingController();
  final _email = TextEditingController();
  final _location = TextEditingController();
  final _links = TextEditingController();
  final _summary = TextEditingController();
  final _skills = TextEditingController();

  final _expIds = <String>[];
  final _expTitles = <TextEditingController>[];
  final _expCompanies = <TextEditingController>[];
  final _expStarts = <TextEditingController>[];
  final _expEnds = <TextEditingController>[];
  final _expSummaries = <TextEditingController>[];
  final _expBullets = <TextEditingController>[];

  final _eduSchools = <TextEditingController>[];
  final _eduDegrees = <TextEditingController>[];
  final _eduEnds = <TextEditingController>[];

  final _projIds = <String>[];
  final _projTitles = <TextEditingController>[];
  final _projStarts = <TextEditingController>[];
  final _projEnds = <TextEditingController>[];
  final _projSummaries = <TextEditingController>[];
  final _projBullets = <TextEditingController>[];

  Map<String, dynamic> _meta = {};
  int _expCount = 0;
  int _eduCount = 0;
  int _projCount = 0;

  @override
  void initState() {
    super.initState();
    applyDocument(widget.initialDocument);
  }

  @override
  void didUpdateWidget(covariant ResumeDocumentForm oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (!identical(oldWidget.initialDocument, widget.initialDocument)) {
      applyDocument(widget.initialDocument);
    }
  }

  @override
  void dispose() {
    _name.dispose();
    _email.dispose();
    _location.dispose();
    _links.dispose();
    _summary.dispose();
    _skills.dispose();
    _disposeLists();
    super.dispose();
  }

  void _disposeLists() {
    for (final c in [
      ..._expTitles,
      ..._expCompanies,
      ..._expStarts,
      ..._expEnds,
      ..._expSummaries,
      ..._expBullets,
      ..._eduSchools,
      ..._eduDegrees,
      ..._eduEnds,
      ..._projTitles,
      ..._projStarts,
      ..._projEnds,
      ..._projSummaries,
      ..._projBullets,
    ]) {
      c.dispose();
    }
    _expIds.clear();
    _expTitles.clear();
    _expCompanies.clear();
    _expStarts.clear();
    _expEnds.clear();
    _expSummaries.clear();
    _expBullets.clear();
    _eduSchools.clear();
    _eduDegrees.clear();
    _eduEnds.clear();
    _projIds.clear();
    _projTitles.clear();
    _projStarts.clear();
    _projEnds.clear();
    _projSummaries.clear();
    _projBullets.clear();
  }

  String _bulletsText(dynamic raw) {
    if (raw is! List) return '';
    return raw.map((e) => '$e'.trim()).where((e) => e.isNotEmpty).join('\n');
  }

  List<String> _bulletsFromText(String text) {
    return text
        .split('\n')
        .map((e) => e.trim())
        .where((e) => e.isNotEmpty)
        .toList();
  }

  String _skillsText(dynamic raw) {
    if (raw is! List) return '';
    final labels = <String>[];
    for (final group in raw) {
      if (group is String && group.trim().isNotEmpty) {
        labels.add(group.trim());
      } else if (group is Map) {
        final keywords = group['keywords'] as List? ?? [];
        if (keywords.isNotEmpty) {
          labels.addAll(
            keywords.map((e) => '$e'.trim()).where((e) => e.isNotEmpty),
          );
        } else if ('${group['name'] ?? ''}'.trim().isNotEmpty) {
          labels.add('${group['name']}'.trim());
        }
      }
    }
    return labels.join(', ');
  }

  List<Map<String, dynamic>> _skillsFromText(String text) {
    final keywords = text
        .split(RegExp(r'[,·\n]'))
        .map((e) => e.trim())
        .where((e) => e.isNotEmpty)
        .toList();
    if (keywords.isEmpty) return [];
    return [
      {'name': '', 'keywords': keywords},
    ];
  }

  /// Reload all fields from a ResumeDocument map (e.g. after agentic propose).
  void applyDocument(Map<String, dynamic> data) {
    final basics = Map<String, dynamic>.from(
      (data['basics'] as Map?) ?? const {},
    );
    final experience = (data['experience'] as List? ?? [])
        .whereType<Map>()
        .map((e) => Map<String, dynamic>.from(e))
        .toList();
    final education = (data['education'] as List? ?? [])
        .whereType<Map>()
        .map((e) => Map<String, dynamic>.from(e))
        .toList();
    final projects = (data['projects'] as List? ?? [])
        .whereType<Map>()
        .map((e) => Map<String, dynamic>.from(e))
        .toList();

    _disposeLists();

    for (var i = 0; i < experience.length; i++) {
      final e = experience[i];
      _expIds.add('${e['id'] ?? ''}'.trim());
      _expTitles.add(TextEditingController(text: '${e['title'] ?? ''}'));
      _expCompanies.add(TextEditingController(text: '${e['company'] ?? ''}'));
      _expStarts.add(TextEditingController(text: '${e['start'] ?? ''}'));
      _expEnds.add(TextEditingController(text: '${e['end'] ?? ''}'));
      _expSummaries.add(TextEditingController(text: '${e['summary'] ?? ''}'));
      _expBullets.add(TextEditingController(text: _bulletsText(e['bullets'])));
    }
    for (final e in education) {
      _eduSchools.add(TextEditingController(text: '${e['school'] ?? ''}'));
      _eduDegrees.add(TextEditingController(text: '${e['degree'] ?? ''}'));
      _eduEnds.add(TextEditingController(text: '${e['end'] ?? ''}'));
    }
    for (var i = 0; i < projects.length; i++) {
      final e = projects[i];
      _projIds.add('${e['id'] ?? ''}'.trim());
      _projTitles.add(TextEditingController(text: '${e['title'] ?? ''}'));
      _projStarts.add(TextEditingController(text: '${e['start'] ?? ''}'));
      _projEnds.add(TextEditingController(text: '${e['end'] ?? ''}'));
      _projSummaries.add(TextEditingController(text: '${e['summary'] ?? ''}'));
      _projBullets.add(TextEditingController(text: _bulletsText(e['bullets'])));
    }

    _name.text = '${basics['name'] ?? ''}';
    _email.text = '${basics['email'] ?? ''}';
    _location.text = '${basics['location'] ?? ''}';
    final links = basics['links'];
    _links.text = links is List ? links.join(' · ') : '${links ?? ''}';
    _summary.text = '${data['summary'] ?? ''}';
    _skills.text = _skillsText(data['skills']);
    _meta = Map<String, dynamic>.from((data['meta'] as Map?) ?? const {});
    _expCount = experience.length;
    _eduCount = education.length;
    _projCount = projects.length;

    if (mounted) setState(() {});
  }

  /// Current form values as a ResumeDocument-shaped map.
  Map<String, dynamic> toDocument() {
    final links = _links.text
        .split('·')
        .map((e) => e.trim())
        .where((e) => e.isNotEmpty)
        .toList();
    final experience = <Map<String, dynamic>>[];
    for (var i = 0; i < _expCount; i++) {
      experience.add({
        'id': _expIds[i],
        'title': _expTitles[i].text.trim(),
        'company': _expCompanies[i].text.trim(),
        'start': _expStarts[i].text.trim(),
        'end': _expEnds[i].text.trim(),
        'summary': _expSummaries[i].text.trim(),
        'bullets': _bulletsFromText(_expBullets[i].text),
      });
    }
    final education = <Map<String, dynamic>>[];
    for (var i = 0; i < _eduCount; i++) {
      education.add({
        'school': _eduSchools[i].text.trim(),
        'degree': _eduDegrees[i].text.trim(),
        'end': _eduEnds[i].text.trim(),
      });
    }
    final projects = <Map<String, dynamic>>[];
    for (var i = 0; i < _projCount; i++) {
      projects.add({
        'id': _projIds[i],
        'title': _projTitles[i].text.trim(),
        'start': _projStarts[i].text.trim(),
        'end': _projEnds[i].text.trim(),
        'summary': _projSummaries[i].text.trim(),
        'bullets': _bulletsFromText(_projBullets[i].text),
      });
    }
    return {
      'meta': _meta,
      'basics': {
        'name': _name.text.trim(),
        'email': _email.text.trim(),
        'location': _location.text.trim(),
        'links': links,
      },
      'summary': _summary.text.trim(),
      'skills': _skillsFromText(_skills.text),
      'experience': experience,
      'education': education,
      'projects': projects,
    };
  }

  void _addExperience() {
    setState(() {
      _expIds.add('');
      _expTitles.add(TextEditingController());
      _expCompanies.add(TextEditingController());
      _expStarts.add(TextEditingController());
      _expEnds.add(TextEditingController());
      _expSummaries.add(TextEditingController());
      _expBullets.add(TextEditingController());
      _expCount++;
    });
  }

  void _removeExperience(int i) {
    setState(() {
      for (final c in [
        _expTitles.removeAt(i),
        _expCompanies.removeAt(i),
        _expStarts.removeAt(i),
        _expEnds.removeAt(i),
        _expSummaries.removeAt(i),
        _expBullets.removeAt(i),
      ]) {
        c.dispose();
      }
      _expIds.removeAt(i);
      _expCount--;
    });
  }

  void _addEducation() {
    setState(() {
      _eduSchools.add(TextEditingController());
      _eduDegrees.add(TextEditingController());
      _eduEnds.add(TextEditingController());
      _eduCount++;
    });
  }

  void _removeEducation(int i) {
    setState(() {
      for (final c in [
        _eduSchools.removeAt(i),
        _eduDegrees.removeAt(i),
        _eduEnds.removeAt(i),
      ]) {
        c.dispose();
      }
      _eduCount--;
    });
  }

  void _addProject() {
    setState(() {
      _projIds.add('');
      _projTitles.add(TextEditingController());
      _projStarts.add(TextEditingController());
      _projEnds.add(TextEditingController());
      _projSummaries.add(TextEditingController());
      _projBullets.add(TextEditingController());
      _projCount++;
    });
  }

  void _removeProject(int i) {
    setState(() {
      for (final c in [
        _projTitles.removeAt(i),
        _projStarts.removeAt(i),
        _projEnds.removeAt(i),
        _projSummaries.removeAt(i),
        _projBullets.removeAt(i),
      ]) {
        c.dispose();
      }
      _projIds.removeAt(i);
      _projCount--;
    });
  }

  InputDecoration _fieldDecoration(String label) {
    return InputDecoration(
      labelText: label,
      border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
    );
  }

  Widget _sectionHeader(
    BuildContext context, {
    required String title,
    required String addLabel,
    required VoidCallback onAdd,
  }) {
    final type = Theme.of(context).textTheme;
    return Row(
      children: [
        Expanded(child: Text(title, style: type.titleMedium)),
        TextButton.icon(
          onPressed: onAdd,
          icon: const Icon(Icons.add, size: 18),
          label: Text(addLabel),
        ),
      ],
    );
  }

  Widget _rowActions({
    required VoidCallback onRemove,
    VoidCallback? onDeepen,
    required String deepenLabel,
  }) {
    return Padding(
      padding: const EdgeInsets.only(top: AppSpacing.grid),
      child: Wrap(
        spacing: AppSpacing.grid,
        runSpacing: AppSpacing.grid / 2,
        children: [
          if (onDeepen != null && widget.enableDeepen)
            OutlinedButton.icon(
              onPressed: onDeepen,
              icon: const Icon(Icons.auto_awesome_outlined, size: 18),
              label: Text(deepenLabel),
            ),
          TextButton(
            onPressed: onRemove,
            style: TextButton.styleFrom(
              foregroundColor: Theme.of(context).colorScheme.error,
            ),
            child: const Text('Remove'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final type = Theme.of(context).textTheme;
    final colors = context.appColors;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text('Basics', style: type.titleMedium),
        const SizedBox(height: AppSpacing.grid),
        TextField(controller: _name, decoration: _fieldDecoration('Full name')),
        const SizedBox(height: AppSpacing.grid),
        TextField(controller: _email, decoration: _fieldDecoration('Email')),
        const SizedBox(height: AppSpacing.grid),
        TextField(
          controller: _location,
          decoration: _fieldDecoration('Location'),
        ),
        const SizedBox(height: AppSpacing.grid),
        TextField(controller: _links, decoration: _fieldDecoration('Links')),
        const SizedBox(height: AppSpacing.grid),
        TextField(
          controller: _summary,
          maxLines: 4,
          decoration: _fieldDecoration('Profile summary'),
        ),
        const SizedBox(height: AppSpacing.grid * 3),
        Text('Skills', style: type.titleMedium),
        const SizedBox(height: AppSpacing.grid),
        TextField(
          controller: _skills,
          maxLines: 3,
          decoration: _fieldDecoration('Skills (comma-separated)'),
        ),
        const SizedBox(height: AppSpacing.grid),
        Text(
          'Edit or remove skills. Agentic edits also use this list.',
          style: type.bodySmall?.copyWith(color: colors.muted),
        ),
        const SizedBox(height: AppSpacing.grid * 3),
        _sectionHeader(
          context,
          title: 'Experience',
          addLabel: 'Add role',
          onAdd: _addExperience,
        ),
        const SizedBox(height: AppSpacing.grid),
        if (_expCount == 0)
          Text(
            'No experience entries. Add a stub role anytime — deepen is optional.',
            style: type.bodyMedium?.copyWith(color: colors.muted),
          ),
        ...List.generate(_expCount, (i) {
          return Padding(
            padding: const EdgeInsets.only(bottom: AppSpacing.grid * 3),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                TextField(
                  controller: _expTitles[i],
                  decoration: _fieldDecoration('Title'),
                ),
                const SizedBox(height: AppSpacing.grid),
                TextField(
                  controller: _expCompanies[i],
                  decoration: _fieldDecoration('Company'),
                ),
                const SizedBox(height: AppSpacing.grid),
                Row(
                  children: [
                    Expanded(
                      child: TextField(
                        controller: _expStarts[i],
                        decoration: _fieldDecoration('Start'),
                      ),
                    ),
                    const SizedBox(width: AppSpacing.grid),
                    Expanded(
                      child: TextField(
                        controller: _expEnds[i],
                        decoration: _fieldDecoration('End'),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: AppSpacing.grid),
                TextField(
                  controller: _expSummaries[i],
                  maxLines: 3,
                  decoration: _fieldDecoration('Summary'),
                ),
                const SizedBox(height: AppSpacing.grid),
                TextField(
                  controller: _expBullets[i],
                  maxLines: 5,
                  decoration: _fieldDecoration('Bullets (one per line)'),
                ),
                _rowActions(
                  onRemove: () => _removeExperience(i),
                  onDeepen: widget.onDeepenExperience == null
                      ? null
                      : () => widget.onDeepenExperience!(i),
                  deepenLabel: 'Deepen',
                ),
              ],
            ),
          );
        }),
        _sectionHeader(
          context,
          title: 'Education',
          addLabel: 'Add education',
          onAdd: _addEducation,
        ),
        const SizedBox(height: AppSpacing.grid),
        if (_eduCount == 0)
          Text(
            'No education entries.',
            style: type.bodyMedium?.copyWith(color: colors.muted),
          ),
        ...List.generate(_eduCount, (i) {
          return Padding(
            padding: const EdgeInsets.only(bottom: AppSpacing.grid * 3),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                TextField(
                  controller: _eduSchools[i],
                  decoration: _fieldDecoration('School'),
                ),
                const SizedBox(height: AppSpacing.grid),
                TextField(
                  controller: _eduDegrees[i],
                  decoration: _fieldDecoration('Degree'),
                ),
                const SizedBox(height: AppSpacing.grid),
                TextField(
                  controller: _eduEnds[i],
                  decoration: _fieldDecoration('End'),
                ),
                _rowActions(
                  onRemove: () => _removeEducation(i),
                  deepenLabel: '',
                ),
              ],
            ),
          );
        }),
        _sectionHeader(
          context,
          title: 'Projects',
          addLabel: 'Add project',
          onAdd: _addProject,
        ),
        const SizedBox(height: AppSpacing.grid),
        if (_projCount == 0)
          Text(
            'No project entries.',
            style: type.bodyMedium?.copyWith(color: colors.muted),
          ),
        ...List.generate(_projCount, (i) {
          return Padding(
            padding: const EdgeInsets.only(bottom: AppSpacing.grid * 3),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                TextField(
                  controller: _projTitles[i],
                  decoration: _fieldDecoration('Title'),
                ),
                const SizedBox(height: AppSpacing.grid),
                Row(
                  children: [
                    Expanded(
                      child: TextField(
                        controller: _projStarts[i],
                        decoration: _fieldDecoration('Start'),
                      ),
                    ),
                    const SizedBox(width: AppSpacing.grid),
                    Expanded(
                      child: TextField(
                        controller: _projEnds[i],
                        decoration: _fieldDecoration('End'),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: AppSpacing.grid),
                TextField(
                  controller: _projSummaries[i],
                  maxLines: 3,
                  decoration: _fieldDecoration('Summary'),
                ),
                const SizedBox(height: AppSpacing.grid),
                TextField(
                  controller: _projBullets[i],
                  maxLines: 5,
                  decoration: _fieldDecoration('Bullets (one per line)'),
                ),
                _rowActions(
                  onRemove: () => _removeProject(i),
                  onDeepen: widget.onDeepenProject == null
                      ? null
                      : () => widget.onDeepenProject!(i),
                  deepenLabel: 'Deepen',
                ),
              ],
            ),
          );
        }),
      ],
    );
  }
}
