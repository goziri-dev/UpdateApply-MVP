import 'package:flutter/material.dart';

/// Extra brand / auth tokens that are not plain [ColorScheme] roles.
///
/// Mapped 1:1 from `prototypes/auth/styles.css` / DESIGN.md.
class AppColors extends ThemeExtension<AppColors> {
  const AppColors({
    required this.link,
    required this.label,
    required this.muted,
    required this.dangerBg,
    required this.inputBorder,
    required this.oauthBorder,
    required this.legal,
  });

  final Color link;
  final Color label;
  final Color muted;
  final Color dangerBg;
  final Color inputBorder;
  final Color oauthBorder;
  final Color legal;

  static const light = AppColors(
    link: Color(0xFF2F6FED),
    label: Color(0xFF3A3A3A),
    muted: Color(0xFF6B6B6B),
    dangerBg: Color(0xFFF8E8E8),
    inputBorder: Color(0xFF111111),
    oauthBorder: Color(0xFFE8E8E8),
    legal: Color(0xFF9A9A9A),
  );

  @override
  AppColors copyWith({
    Color? link,
    Color? label,
    Color? muted,
    Color? dangerBg,
    Color? inputBorder,
    Color? oauthBorder,
    Color? legal,
  }) {
    return AppColors(
      link: link ?? this.link,
      label: label ?? this.label,
      muted: muted ?? this.muted,
      dangerBg: dangerBg ?? this.dangerBg,
      inputBorder: inputBorder ?? this.inputBorder,
      oauthBorder: oauthBorder ?? this.oauthBorder,
      legal: legal ?? this.legal,
    );
  }

  @override
  AppColors lerp(ThemeExtension<AppColors>? other, double t) {
    if (other is! AppColors) return this;
    return AppColors(
      link: Color.lerp(link, other.link, t)!,
      label: Color.lerp(label, other.label, t)!,
      muted: Color.lerp(muted, other.muted, t)!,
      dangerBg: Color.lerp(dangerBg, other.dangerBg, t)!,
      inputBorder: Color.lerp(inputBorder, other.inputBorder, t)!,
      oauthBorder: Color.lerp(oauthBorder, other.oauthBorder, t)!,
      legal: Color.lerp(legal, other.legal, t)!,
    );
  }
}

extension AppColorsX on BuildContext {
  AppColors get appColors =>
      Theme.of(this).extension<AppColors>() ?? AppColors.light;
}
