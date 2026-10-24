import 'package:flutter/material.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_theme.dart';

/// Shared in-place editor for a `ResumeDocument` map.
///
/// Collapsible sections (Basics / Skills / Experience / …) with expandable
/// items. Bullets and skills are discrete list rows.
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
  static const double _fieldRadius = 8;

  final _name = TextEditingController();
  final _email = TextEditingController();
  final _location = TextEditingController();
  final _links = TextEditingController();
  final _summary = TextEditingController();
  final _skillItems = <TextEditingController>[];
  final _skillAdd = TextEditingController();

  final _expIds = <String>[];
  final _expTitles = <TextEditingController>[];
  final _expCompanies = <TextEditingController>[];
  final _expStarts = <TextEditingController>[];
  final _expEnds = <TextEditingController>[];
  final _expSummaries = <TextEditingController>[];
  final _expBullets = <List<TextEditingController>>[];

  final _eduSchools = <TextEditingController>[];
  final _eduDegrees = <TextEditingController>[];
  final _eduEnds = <TextEditingController>[];
  final _eduKinds = <String>[];

  final _projIds = <String>[];
  final _projTitles = <TextEditingController>[];
  final _projStarts = <TextEditingController>[];
  final _projEnds = <TextEditingController>[];
  final _projSummaries = <TextEditingController>[];
  final _projBullets = <List<TextEditingController>>[];

  Map<String, dynamic> _meta = {};
  int _expCount = 0;
  int _eduCount = 0;
  int _projCount = 0;

  /// Top-level sections (multiple may be open). Default: all collapsed.
  bool _basicsOpen = false;
  bool _skillsOpen = false;
  bool _experienceOpen = false;
  bool _educationOpen = false;
  bool _projectsOpen = false;

  /// Expanded item indexes within each list section.
  final Set<int> _openExp = {};
  final Set<int> _openEdu = {};
  final Set<int> _openProj = {};

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
    _skillAdd.dispose();
    _disposeLists();
    super.dispose();
  }

  void _disposeControllers(Iterable<TextEditingController> controllers) {
    for (final c in controllers) {
      c.dispose();
    }
  }

  void _disposeLists() {
    _disposeControllers([
      ..._expTitles,
      ..._expCompanies,
      ..._expStarts,
      ..._expEnds,
      ..._expSummaries,
      for (final bullets in _expBullets) ...bullets,
      ..._eduSchools,
      ..._eduDegrees,
      ..._eduEnds,
      ..._projTitles,
      ..._projStarts,
      ..._projEnds,
      ..._projSummaries,
      for (final bullets in _projBullets) ...bullets,
      ..._skillItems,
    ]);
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
    _eduKinds.clear();
    _projIds.clear();
    _projTitles.clear();
    _projStarts.clear();
    _projEnds.clear();
    _projSummaries.clear();
    _projBullets.clear();
    _skillItems.clear();
  }

  String _stripBulletPrefix(String raw) {
    var text = raw.trim();
    if (text.startsWith('•') ||
        text.startsWith('·') ||
        text.startsWith('-') ||
        text.startsWith('*')) {
      text = text.substring(1).trim();
    }
    return text;
  }

  List<String> _bulletStrings(dynamic raw) {
    if (raw is! List) return [];
    return raw
        .map((e) => _stripBulletPrefix('$e'))
        .where((e) => e.isNotEmpty)
        .toList();
  }

  List<TextEditingController> _controllersFromBullets(dynamic raw) {
    final items = _bulletStrings(raw);
    if (items.isEmpty) {
      return [TextEditingController()];
    }
    return [for (final item in items) TextEditingController(text: item)];
  }

  List<String> _stringsFromControllers(
    List<TextEditingController> controllers,
  ) {
    return controllers
        .map((c) => _stripBulletPrefix(c.text))
        .where((e) => e.isNotEmpty)
        .toList();
  }

  List<String> _skillLabels(dynamic raw) {
    if (raw is! List) return [];
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
    return labels;
  }

  List<Map<String, dynamic>> _skillsFromControllers() {
    final keywords = _stringsFromControllers(_skillItems);
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
      _expBullets.add(_controllersFromBullets(e['bullets']));
    }
    for (final e in education) {
      _eduSchools.add(TextEditingController(text: '${e['school'] ?? ''}'));
      _eduDegrees.add(TextEditingController(text: '${e['degree'] ?? ''}'));
      _eduEnds.add(TextEditingController(text: '${e['end'] ?? ''}'));
      _eduKinds.add('${e['kind'] ?? ''}'.trim());
    }
    for (var i = 0; i < projects.length; i++) {
      final e = projects[i];
      _projIds.add('${e['id'] ?? ''}'.trim());
      _projTitles.add(TextEditingController(text: '${e['title'] ?? ''}'));
      _projStarts.add(TextEditingController(text: '${e['start'] ?? ''}'));
      _projEnds.add(TextEditingController(text: '${e['end'] ?? ''}'));
      _projSummaries.add(TextEditingController(text: '${e['summary'] ?? ''}'));
      _projBullets.add(_controllersFromBullets(e['bullets']));
    }

    for (final label in _skillLabels(data['skills'])) {
      _skillItems.add(TextEditingController(text: label));
    }

    _name.text = '${basics['name'] ?? ''}';
    _email.text = '${basics['email'] ?? ''}';
    _location.text = '${basics['location'] ?? ''}';
    final links = basics['links'];
    _links.text = links is List ? links.join(' · ') : '${links ?? ''}';
    _summary.text = '${data['summary'] ?? ''}';
    _meta = Map<String, dynamic>.from((data['meta'] as Map?) ?? const {});
    _expCount = experience.length;
    _eduCount = education.length;
    _projCount = projects.length;
    _openExp.clear();
    _openEdu.clear();
    _openProj.clear();

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
        'bullets': _stringsFromControllers(_expBullets[i]),
      });
    }
    final education = <Map<String, dynamic>>[];
    for (var i = 0; i < _eduCount; i++) {
      education.add({
        'school': _eduSchools[i].text.trim(),
        'degree': _eduDegrees[i].text.trim(),
        'end': _eduEnds[i].text.trim(),
        if (_eduKinds[i].trim().isNotEmpty) 'kind': _eduKinds[i].trim(),
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
        'bullets': _stringsFromControllers(_projBullets[i]),
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
      'skills': _skillsFromControllers(),
      'experience': experience,
      'education': education,
      'projects': projects,
    };
  }

  void _shiftOpenIndexes(Set<int> open, int removed) {
    final next = <int>{};
    for (final i in open) {
      if (i < removed) {
        next.add(i);
      } else if (i > removed) {
        next.add(i - 1);
      }
    }
    open
      ..clear()
      ..addAll(next);
  }

  void _addExperience() {
    setState(() {
      _expIds.add('');
      _expTitles.add(TextEditingController());
      _expCompanies.add(TextEditingController());
      _expStarts.add(TextEditingController());
      _expEnds.add(TextEditingController());
      _expSummaries.add(TextEditingController());
      _expBullets.add([TextEditingController()]);
      _expCount++;
      _experienceOpen = true;
      _openExp.add(_expCount - 1);
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
      ]) {
        c.dispose();
      }
      _disposeControllers(_expBullets.removeAt(i));
      _expIds.removeAt(i);
      _expCount--;
      _shiftOpenIndexes(_openExp, i);
    });
  }

  void _addEducation() {
    setState(() {
      _eduSchools.add(TextEditingController());
      _eduDegrees.add(TextEditingController());
      _eduEnds.add(TextEditingController());
      _eduKinds.add('');
      _eduCount++;
      _educationOpen = true;
      _openEdu.add(_eduCount - 1);
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
      _eduKinds.removeAt(i);
      _eduCount--;
      _shiftOpenIndexes(_openEdu, i);
    });
  }

  void _addProject() {
    setState(() {
      _projIds.add('');
      _projTitles.add(TextEditingController());
      _projStarts.add(TextEditingController());
      _projEnds.add(TextEditingController());
      _projSummaries.add(TextEditingController());
      _projBullets.add([TextEditingController()]);
      _projCount++;
      _projectsOpen = true;
      _openProj.add(_projCount - 1);
    });
  }

  void _removeProject(int i) {
    setState(() {
      for (final c in [
        _projTitles.removeAt(i),
        _projStarts.removeAt(i),
        _projEnds.removeAt(i),
        _projSummaries.removeAt(i),
      ]) {
        c.dispose();
      }
      _disposeControllers(_projBullets.removeAt(i));
      _projIds.removeAt(i);
      _projCount--;
      _shiftOpenIndexes(_openProj, i);
    });
  }

  String _itemLabel(String primary, String secondary) {
    final a = primary.trim();
    final b = secondary.trim();
    if (a.isEmpty && b.isEmpty) return 'Untitled';
    if (a.isEmpty) return b;
    if (b.isEmpty) return a;
    return '$a · $b';
  }

  void _addBullet(List<TextEditingController> bullets) {
    setState(() => bullets.add(TextEditingController()));
  }

  void _removeBullet(List<TextEditingController> bullets, int index) {
    setState(() {
      bullets.removeAt(index).dispose();
      if (bullets.isEmpty) {
        bullets.add(TextEditingController());
      }
    });
  }

  void _addSkillFromField() {
    final text = _skillAdd.text.trim();
    if (text.isEmpty) return;
    setState(() {
      _skillItems.add(TextEditingController(text: text));
      _skillAdd.clear();
    });
  }

  void _removeSkill(int index) {
    setState(() => _skillItems.removeAt(index).dispose());
  }

  InputDecoration _fieldDecoration(String label) {
    const side = BorderSide(color: Color(0xFF111111), width: 1.5);
    final radius = BorderRadius.circular(_fieldRadius);
    return InputDecoration(
      labelText: label,
      border: OutlineInputBorder(borderRadius: radius, borderSide: side),
      enabledBorder: OutlineInputBorder(borderRadius: radius, borderSide: side),
      focusedBorder: OutlineInputBorder(
        borderRadius: radius,
        borderSide: BorderSide(
          color: Theme.of(context).colorScheme.primary,
          width: 1.5,
        ),
      ),
      errorBorder: OutlineInputBorder(
        borderRadius: radius,
        borderSide: BorderSide(
          color: Theme.of(context).colorScheme.error,
          width: 1.5,
        ),
      ),
    );
  }

  InputDecoration _listItemDecoration({String? hint}) {
    final scheme = Theme.of(context).colorScheme;
    final muted = BorderSide(color: scheme.outlineVariant, width: 1);
    final radius = BorderRadius.circular(_fieldRadius);
    return InputDecoration(
      hintText: hint,
      isDense: true,
      filled: true,
      fillColor: scheme.surface,
      contentPadding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.grid * 1.5,
        vertical: AppSpacing.grid * 1.25,
      ),
      border: OutlineInputBorder(borderRadius: radius, borderSide: muted),
      enabledBorder: OutlineInputBorder(
        borderRadius: radius,
        borderSide: muted,
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: radius,
        borderSide: BorderSide(color: scheme.primary, width: 1.5),
      ),
    );
  }

  Widget _collapsibleSection({
    required String title,
    required bool open,
    required ValueChanged<bool> onOpenChanged,
    required Widget child,
    String? subtitle,
    String? addLabel,
    VoidCallback? onAdd,
  }) {
    final type = Theme.of(context).textTheme;
    final colors = context.appColors;
    final scheme = Theme.of(context).colorScheme;
    return DecoratedBox(
      decoration: BoxDecoration(
        border: Border.all(color: scheme.outlineVariant),
        borderRadius: BorderRadius.circular(_fieldRadius),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          InkWell(
            borderRadius: BorderRadius.circular(_fieldRadius),
            onTap: () => onOpenChanged(!open),
            child: Padding(
              padding: const EdgeInsets.symmetric(
                horizontal: AppSpacing.grid * 1.5,
                vertical: AppSpacing.grid * 1.25,
              ),
              child: Row(
                children: [
                  Icon(
                    open ? Icons.expand_less : Icons.expand_more,
                    size: 22,
                    color: colors.muted,
                  ),
                  const SizedBox(width: AppSpacing.grid),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(title, style: type.titleMedium),
                        if (subtitle != null && subtitle.isNotEmpty)
                          Text(
                            subtitle,
                            style: type.bodySmall?.copyWith(
                              color: colors.muted,
                            ),
                          ),
                      ],
                    ),
                  ),
                  if (addLabel != null && onAdd != null)
                    TextButton.icon(
                      onPressed: onAdd,
                      icon: const Icon(Icons.add, size: 18),
                      label: Text(addLabel),
                    ),
                ],
              ),
            ),
          ),
          if (open)
            Padding(
              padding: const EdgeInsets.fromLTRB(
                AppSpacing.grid * 1.5,
                0,
                AppSpacing.grid * 1.5,
                AppSpacing.grid * 1.5,
              ),
              child: child,
            ),
        ],
      ),
    );
  }

  Widget _collapsibleItem({
    required String title,
    required String subtitle,
    required bool open,
    required ValueChanged<bool> onOpenChanged,
    required Widget child,
  }) {
    final type = Theme.of(context).textTheme;
    final colors = context.appColors;
    final scheme = Theme.of(context).colorScheme;
    return DecoratedBox(
      decoration: BoxDecoration(
        color: scheme.surfaceContainerHighest.withValues(alpha: 0.45),
        borderRadius: BorderRadius.circular(_fieldRadius),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          InkWell(
            borderRadius: BorderRadius.circular(_fieldRadius),
            onTap: () => onOpenChanged(!open),
            child: Padding(
              padding: const EdgeInsets.symmetric(
                horizontal: AppSpacing.grid * 1.25,
                vertical: AppSpacing.grid,
              ),
              child: Row(
                children: [
                  Icon(
                    open ? Icons.expand_less : Icons.expand_more,
                    size: 20,
                    color: colors.muted,
                  ),
                  const SizedBox(width: AppSpacing.grid),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(title, style: type.bodyLarge),
                        if (subtitle.isNotEmpty)
                          Text(
                            subtitle,
                            style: type.bodySmall?.copyWith(
                              color: colors.muted,
                            ),
                          ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
          if (open)
            Padding(
              padding: const EdgeInsets.fromLTRB(
                AppSpacing.grid * 1.25,
                0,
                AppSpacing.grid * 1.25,
                AppSpacing.grid * 1.25,
              ),
              child: child,
            ),
        ],
      ),
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

  Widget _bulletListEditor(List<TextEditingController> bullets) {
    final type = Theme.of(context).textTheme;
    final colors = context.appColors;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text('Bullets', style: type.bodySmall?.copyWith(color: colors.label)),
        const SizedBox(height: AppSpacing.grid),
        ...List.generate(bullets.length, (i) {
          return Padding(
            padding: const EdgeInsets.only(bottom: AppSpacing.grid),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Padding(
                  padding: const EdgeInsets.only(top: 10),
                  child: Text(
                    '•',
                    style: type.bodyLarge?.copyWith(height: 1.2),
                  ),
                ),
                const SizedBox(width: AppSpacing.grid),
                Expanded(
                  child: TextField(
                    controller: bullets[i],
                    minLines: 1,
                    maxLines: 4,
                    textInputAction: TextInputAction.newline,
                    decoration: _listItemDecoration(hint: 'Bullet'),
                  ),
                ),
                IconButton(
                  tooltip: 'Remove bullet',
                  onPressed:
                      bullets.length <= 1 && bullets[i].text.trim().isEmpty
                      ? null
                      : () => _removeBullet(bullets, i),
                  icon: const Icon(Icons.close, size: 18),
                ),
              ],
            ),
          );
        }),
        Align(
          alignment: Alignment.centerLeft,
          child: TextButton.icon(
            onPressed: () => _addBullet(bullets),
            icon: const Icon(Icons.add, size: 18),
            label: const Text('Add bullet'),
          ),
        ),
      ],
    );
  }

  /// Show 4 skill rows before scrolling.
  static const int _skillsVisibleMax = 4;
  static const double _skillRowExtent = 56;

  Widget _skillsEditor() {
    final type = Theme.of(context).textTheme;
    final colors = context.appColors;
    final list = _skillItems.isEmpty
        ? Padding(
            padding: const EdgeInsets.only(bottom: AppSpacing.grid),
            child: Text(
              'No skills yet.',
              style: type.bodyMedium?.copyWith(color: colors.muted),
            ),
          )
        : ConstrainedBox(
            constraints: const BoxConstraints(
              maxHeight: _skillsVisibleMax * _skillRowExtent,
            ),
            child: ListView.builder(
              shrinkWrap: true,
              primary: false,
              itemCount: _skillItems.length,
              itemBuilder: (context, i) {
                return Padding(
                  padding: const EdgeInsets.only(bottom: AppSpacing.grid),
                  child: SizedBox(
                    height: _skillRowExtent - AppSpacing.grid,
                    child: Row(
                      children: [
                        Expanded(
                          child: TextField(
                            controller: _skillItems[i],
                            decoration: _listItemDecoration(hint: 'Skill'),
                          ),
                        ),
                        IconButton(
                          tooltip: 'Remove skill',
                          onPressed: () => _removeSkill(i),
                          icon: const Icon(Icons.close, size: 18),
                        ),
                      ],
                    ),
                  ),
                );
              },
            ),
          );
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        list,
        if (_skillItems.length > _skillsVisibleMax)
          Padding(
            padding: const EdgeInsets.only(bottom: AppSpacing.grid),
            child: Text(
              'Scroll for more (${_skillItems.length})',
              style: type.bodySmall?.copyWith(color: colors.muted),
            ),
          ),
        Row(
          children: [
            Expanded(
              child: TextField(
                controller: _skillAdd,
                textInputAction: TextInputAction.done,
                onSubmitted: (_) => _addSkillFromField(),
                decoration: _listItemDecoration(hint: 'Add a skill'),
              ),
            ),
            const SizedBox(width: AppSpacing.grid),
            TextButton(onPressed: _addSkillFromField, child: const Text('Add')),
          ],
        ),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    final type = Theme.of(context).textTheme;
    final colors = context.appColors;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _collapsibleSection(
          title: 'Basics',
          subtitle: _name.text.trim().isEmpty ? null : _name.text.trim(),
          open: _basicsOpen,
          onOpenChanged: (v) => setState(() => _basicsOpen = v),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              TextField(
                controller: _name,
                decoration: _fieldDecoration('Full name'),
                onChanged: (_) => setState(() {}),
              ),
              const SizedBox(height: AppSpacing.grid),
              TextField(
                controller: _email,
                decoration: _fieldDecoration('Email'),
              ),
              const SizedBox(height: AppSpacing.grid),
              TextField(
                controller: _location,
                decoration: _fieldDecoration('Location'),
              ),
              const SizedBox(height: AppSpacing.grid),
              TextField(
                controller: _links,
                decoration: _fieldDecoration('Links'),
              ),
              const SizedBox(height: AppSpacing.grid),
              TextField(
                controller: _summary,
                maxLines: 4,
                decoration: _fieldDecoration('Profile summary'),
              ),
            ],
          ),
        ),
        const SizedBox(height: AppSpacing.grid * 1.5),
        _collapsibleSection(
          title: 'Skills',
          subtitle: _skillItems.isEmpty
              ? 'None yet'
              : '${_skillItems.length} skill${_skillItems.length == 1 ? '' : 's'}',
          open: _skillsOpen,
          onOpenChanged: (v) => setState(() => _skillsOpen = v),
          child: _skillsEditor(),
        ),
        const SizedBox(height: AppSpacing.grid * 1.5),
        _collapsibleSection(
          title: 'Experience',
          subtitle: _expCount == 0
              ? 'None yet'
              : '$_expCount role${_expCount == 1 ? '' : 's'}',
          open: _experienceOpen,
          onOpenChanged: (v) => setState(() => _experienceOpen = v),
          addLabel: 'Add role',
          onAdd: _addExperience,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              if (_expCount == 0)
                Text(
                  'No experience yet. Add a role anytime.',
                  style: type.bodyMedium?.copyWith(color: colors.muted),
                ),
              ...List.generate(_expCount, (i) {
                final open = _openExp.contains(i);
                final dates =
                    '${_expStarts[i].text.trim()} — ${_expEnds[i].text.trim()}'
                        .replaceAll(RegExp(r'^\s*—\s*$'), '')
                        .trim();
                return Padding(
                  padding: EdgeInsets.only(
                    bottom: i == _expCount - 1 ? 0 : AppSpacing.grid,
                  ),
                  child: _collapsibleItem(
                    title: _itemLabel(
                      _expTitles[i].text,
                      _expCompanies[i].text,
                    ),
                    subtitle: dates,
                    open: open,
                    onOpenChanged: (v) => setState(() {
                      if (v) {
                        _openExp.add(i);
                      } else {
                        _openExp.remove(i);
                      }
                    }),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        TextField(
                          controller: _expTitles[i],
                          decoration: _fieldDecoration('Title'),
                          onChanged: (_) => setState(() {}),
                        ),
                        const SizedBox(height: AppSpacing.grid),
                        TextField(
                          controller: _expCompanies[i],
                          decoration: _fieldDecoration('Company'),
                          onChanged: (_) => setState(() {}),
                        ),
                        const SizedBox(height: AppSpacing.grid),
                        Row(
                          children: [
                            Expanded(
                              child: TextField(
                                controller: _expStarts[i],
                                decoration: _fieldDecoration('Start'),
                                onChanged: (_) => setState(() {}),
                              ),
                            ),
                            const SizedBox(width: AppSpacing.grid),
                            Expanded(
                              child: TextField(
                                controller: _expEnds[i],
                                decoration: _fieldDecoration('End'),
                                onChanged: (_) => setState(() {}),
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
                        _bulletListEditor(_expBullets[i]),
                        _rowActions(
                          onRemove: () => _removeExperience(i),
                          onDeepen: widget.onDeepenExperience == null
                              ? null
                              : () => widget.onDeepenExperience!(i),
                          deepenLabel: 'Deepen',
                        ),
                      ],
                    ),
                  ),
                );
              }),
            ],
          ),
        ),
        const SizedBox(height: AppSpacing.grid * 1.5),
        _collapsibleSection(
          title: 'Education & Certificates',
          subtitle: _eduCount == 0
              ? 'None yet'
              : '$_eduCount entr${_eduCount == 1 ? 'y' : 'ies'}',
          open: _educationOpen,
          onOpenChanged: (v) => setState(() => _educationOpen = v),
          addLabel: 'Add',
          onAdd: _addEducation,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              if (_eduCount == 0)
                Text(
                  'No education or certificates yet.',
                  style: type.bodyMedium?.copyWith(color: colors.muted),
                ),
              ...List.generate(_eduCount, (i) {
                final open = _openEdu.contains(i);
                return Padding(
                  padding: EdgeInsets.only(
                    bottom: i == _eduCount - 1 ? 0 : AppSpacing.grid,
                  ),
                  child: _collapsibleItem(
                    title: _itemLabel(_eduSchools[i].text, _eduDegrees[i].text),
                    subtitle: _eduEnds[i].text.trim(),
                    open: open,
                    onOpenChanged: (v) => setState(() {
                      if (v) {
                        _openEdu.add(i);
                      } else {
                        _openEdu.remove(i);
                      }
                    }),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        TextField(
                          controller: _eduSchools[i],
                          decoration: _fieldDecoration('School / Issuer'),
                          onChanged: (_) => setState(() {}),
                        ),
                        const SizedBox(height: AppSpacing.grid),
                        TextField(
                          controller: _eduDegrees[i],
                          decoration: _fieldDecoration('Degree / Certificate'),
                          onChanged: (_) => setState(() {}),
                        ),
                        const SizedBox(height: AppSpacing.grid),
                        TextField(
                          controller: _eduEnds[i],
                          decoration: _fieldDecoration('End'),
                          onChanged: (_) => setState(() {}),
                        ),
                        _rowActions(
                          onRemove: () => _removeEducation(i),
                          deepenLabel: '',
                        ),
                      ],
                    ),
                  ),
                );
              }),
            ],
          ),
        ),
        const SizedBox(height: AppSpacing.grid * 1.5),
        _collapsibleSection(
          title: 'Projects',
          subtitle: _projCount == 0
              ? 'None yet'
              : '$_projCount project${_projCount == 1 ? '' : 's'}',
          open: _projectsOpen,
          onOpenChanged: (v) => setState(() => _projectsOpen = v),
          addLabel: 'Add project',
          onAdd: _addProject,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              if (_projCount == 0)
                Text(
                  'No project entries.',
                  style: type.bodyMedium?.copyWith(color: colors.muted),
                ),
              ...List.generate(_projCount, (i) {
                final open = _openProj.contains(i);
                final dates =
                    '${_projStarts[i].text.trim()} — ${_projEnds[i].text.trim()}'
                        .replaceAll(RegExp(r'^\s*—\s*$'), '')
                        .trim();
                return Padding(
                  padding: EdgeInsets.only(
                    bottom: i == _projCount - 1 ? 0 : AppSpacing.grid,
                  ),
                  child: _collapsibleItem(
                    title: _itemLabel(_projTitles[i].text, ''),
                    subtitle: dates,
                    open: open,
                    onOpenChanged: (v) => setState(() {
                      if (v) {
                        _openProj.add(i);
                      } else {
                        _openProj.remove(i);
                      }
                    }),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        TextField(
                          controller: _projTitles[i],
                          decoration: _fieldDecoration('Title'),
                          onChanged: (_) => setState(() {}),
                        ),
                        const SizedBox(height: AppSpacing.grid),
                        Row(
                          children: [
                            Expanded(
                              child: TextField(
                                controller: _projStarts[i],
                                decoration: _fieldDecoration('Start'),
                                onChanged: (_) => setState(() {}),
                              ),
                            ),
                            const SizedBox(width: AppSpacing.grid),
                            Expanded(
                              child: TextField(
                                controller: _projEnds[i],
                                decoration: _fieldDecoration('End'),
                                onChanged: (_) => setState(() {}),
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
                        _bulletListEditor(_projBullets[i]),
                        _rowActions(
                          onRemove: () => _removeProject(i),
                          onDeepen: widget.onDeepenProject == null
                              ? null
                              : () => widget.onDeepenProject!(i),
                          deepenLabel: 'Deepen',
                        ),
                      ],
                    ),
                  ),
                );
              }),
            ],
          ),
        ),
      ],
    );
  }
}
