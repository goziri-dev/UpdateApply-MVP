import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import 'app_colors.dart';

/// 8px spacing grid (matches `prototypes/auth/`).
abstract final class AppSpacing {
  static const double grid = 8;
  static const double authColumn = 340;
  static const double pillRadius = 999;
  static const double markRadius = 12;
  static const double controlHeight = 48;
}

class AppTheme {
  const AppTheme._();

  static const Color _accent = Color(0xFF1B4D3E);
  static const Color _accentHover = Color(0xFF153D32);
  static const Color _ink = Color(0xFF111111);
  static const Color _surfaceSoft = Color(0xFFF5F5F5);
  static const Color _danger = Color(0xFF9B2C2C);

  static ThemeData light() {
    final scheme = ColorScheme.light(
      primary: _accent,
      onPrimary: Colors.white,
      primaryContainer: _accentHover,
      onPrimaryContainer: Colors.white,
      surface: Colors.white,
      onSurface: _ink,
      onSurfaceVariant: AppColors.light.muted,
      error: _danger,
      onError: Colors.white,
      errorContainer: AppColors.light.dangerBg,
      onErrorContainer: _danger,
      outline: AppColors.light.oauthBorder,
      outlineVariant: AppColors.light.inputBorder,
      surfaceContainerHighest: _surfaceSoft,
    );

    TextStyle sans({
      double? fontSize,
      FontWeight? fontWeight,
      double? height,
      double? letterSpacing,
      Color? color,
    }) {
      return GoogleFonts.sourceSans3(
        fontSize: fontSize,
        fontWeight: fontWeight,
        height: height,
        letterSpacing: letterSpacing,
        color: color,
      );
    }

    final textTheme = TextTheme(
      headlineMedium: sans(
        fontSize: 28,
        fontWeight: FontWeight.w700,
        height: 1.15,
        letterSpacing: -0.03 * 28,
        color: _ink,
      ),
      titleMedium: sans(fontSize: 16, fontWeight: FontWeight.w500, color: _ink),
      bodyLarge: sans(fontSize: 15, fontWeight: FontWeight.w500, color: _ink),
      bodyMedium: sans(fontSize: 14, fontWeight: FontWeight.w500, color: _ink),
      bodySmall: sans(
        fontSize: 13,
        fontWeight: FontWeight.w600,
        color: AppColors.light.label,
      ),
      labelLarge: sans(fontSize: 15, fontWeight: FontWeight.w600, color: _ink),
      labelSmall: sans(
        fontSize: 12,
        fontWeight: FontWeight.w400,
        color: AppColors.light.legal,
      ),
    );

    return ThemeData(
      colorScheme: scheme,
      useMaterial3: true,
      visualDensity: VisualDensity.adaptivePlatformDensity,
      scaffoldBackgroundColor: Colors.white,
      // Keep MaterialIcons as the icon font — assigning GoogleFonts styles into
      // textTheme alone is fine; never set ThemeData.fontFamily to Source Sans
      // or Icons render as tofu boxes on Flutter web.
      textTheme: textTheme,
      iconTheme: const IconThemeData(color: _ink, size: 24),
      extensions: const [AppColors.light],
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: scheme.primary,
          foregroundColor: scheme.onPrimary,
          disabledBackgroundColor: scheme.primary.withValues(alpha: 0.7),
          disabledForegroundColor: scheme.onPrimary,
          minimumSize: const Size.fromHeight(AppSpacing.controlHeight),
          shape: const StadiumBorder(),
          textStyle: textTheme.labelLarge?.copyWith(color: scheme.onPrimary),
        ),
      ),
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          foregroundColor: AppColors.light.link,
          textStyle: textTheme.bodySmall?.copyWith(
            fontWeight: FontWeight.w600,
            color: AppColors.light.link,
          ),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: Colors.white,
        contentPadding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.grid * 2.5,
          vertical: AppSpacing.grid * 1.75,
        ),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppSpacing.pillRadius),
          borderSide: const BorderSide(color: Color(0xFF111111), width: 1.5),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppSpacing.pillRadius),
          borderSide: const BorderSide(color: Color(0xFF111111), width: 1.5),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppSpacing.pillRadius),
          borderSide: BorderSide(color: scheme.primary, width: 1.5),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppSpacing.pillRadius),
          borderSide: BorderSide(color: scheme.error, width: 1.5),
        ),
        hintStyle: textTheme.bodyLarge?.copyWith(
          color: const Color(0xFFA0A0A0),
          fontWeight: FontWeight.w400,
        ),
      ),
    );
  }
}
