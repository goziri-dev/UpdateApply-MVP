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
    required this.stage,
    required this.accentSoft,
    required this.successBg,
    required this.warnBg,
    required this.warnInk,
    required this.oneTimeBadgeBg,
  });

  final Color link;
  final Color label;
  final Color muted;
  final Color dangerBg;
  final Color inputBorder;
  final Color oauthBorder;
  final Color legal;

  /// Comparison stage wash (`prototypes/paywall` `--stage`).
  final Color stage;

  /// Soft forest tint for recommended badges / balance chip.
  final Color accentSoft;

  final Color successBg;
  final Color warnBg;
  final Color warnInk;
  final Color oneTimeBadgeBg;

  static const light = AppColors(
    link: Color(0xFF2F6FED),
    label: Color(0xFF3A3A3A),
    muted: Color(0xFF6B6B6B),
    dangerBg: Color(0xFFF8E8E8),
    inputBorder: Color(0xFF111111),
    oauthBorder: Color(0xFFE8E8E8),
    legal: Color(0xFF9A9A9A),
    stage: Color(0xFFF3F4F2),
    accentSoft: Color(0xFFE8F0ED),
    successBg: Color(0xFFE8F2EE),
    warnBg: Color(0xFFF7F1E4),
    warnInk: Color(0xFF5C4A28),
    oneTimeBadgeBg: Color(0xFFEEF3FB),
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
    Color? stage,
    Color? accentSoft,
    Color? successBg,
    Color? warnBg,
    Color? warnInk,
    Color? oneTimeBadgeBg,
  }) {
    return AppColors(
      link: link ?? this.link,
      label: label ?? this.label,
      muted: muted ?? this.muted,
      dangerBg: dangerBg ?? this.dangerBg,
      inputBorder: inputBorder ?? this.inputBorder,
      oauthBorder: oauthBorder ?? this.oauthBorder,
      legal: legal ?? this.legal,
      stage: stage ?? this.stage,
      accentSoft: accentSoft ?? this.accentSoft,
      successBg: successBg ?? this.successBg,
      warnBg: warnBg ?? this.warnBg,
      warnInk: warnInk ?? this.warnInk,
      oneTimeBadgeBg: oneTimeBadgeBg ?? this.oneTimeBadgeBg,
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
      stage: Color.lerp(stage, other.stage, t)!,
      accentSoft: Color.lerp(accentSoft, other.accentSoft, t)!,
      successBg: Color.lerp(successBg, other.successBg, t)!,
      warnBg: Color.lerp(warnBg, other.warnBg, t)!,
      warnInk: Color.lerp(warnInk, other.warnInk, t)!,
      oneTimeBadgeBg: Color.lerp(oneTimeBadgeBg, other.oneTimeBadgeBg, t)!,
    );
  }
}

extension AppColorsX on BuildContext {
  AppColors get appColors =>
      Theme.of(this).extension<AppColors>() ?? AppColors.light;
}
