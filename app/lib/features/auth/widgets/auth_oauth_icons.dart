import 'package:flutter/material.dart';

/// Compact brand marks for OAuth pills (paths adapted from `prototypes/auth/`).
class AuthOAuthIcons {
  const AuthOAuthIcons._();

  static Widget google({double size = 18}) {
    return CustomPaint(size: Size.square(size), painter: _GoogleIconPainter());
  }

  static Widget github({
    double size = 18,
    Color color = const Color(0xFF111111),
  }) {
    return CustomPaint(
      size: Size.square(size),
      painter: _GitHubIconPainter(color),
    );
  }

  static Widget notion({
    double size = 18,
    Color color = const Color(0xFF111111),
  }) {
    return CustomPaint(
      size: Size.square(size),
      painter: _NotionIconPainter(color),
    );
  }
}

class _GoogleIconPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final s = size.width / 18;
    canvas.scale(s, s);

    final blue = Paint()..color = const Color(0xFF4285F4);
    final green = Paint()..color = const Color(0xFF34A853);
    final yellow = Paint()..color = const Color(0xFFFBBC05);
    final red = Paint()..color = const Color(0xFFEA4335);

    final pBlue = Path()
      ..moveTo(17.64, 9.2)
      ..cubicTo(17.64, 8.563, 17.583, 7.949, 17.476, 7.36)
      ..lineTo(9, 7.36)
      ..lineTo(9, 10.841)
      ..lineTo(13.844, 10.841)
      ..cubicTo(13.35, 12.15, 12.52, 13.25, 12.048, 13.557)
      ..lineTo(12.048, 15.816)
      ..lineTo(14.956, 15.816)
      ..cubicTo(16.658, 14.249, 17.64, 11.941, 17.64, 9.2)
      ..close();
    canvas.drawPath(pBlue, blue);

    final pGreen = Path()
      ..moveTo(9, 18)
      ..cubicTo(11.43, 18, 13.467, 17.194, 14.956, 15.82)
      ..lineTo(12.048, 13.561)
      ..cubicTo(11.242, 14.101, 10.211, 14.421, 9, 14.421)
      ..cubicTo(6.656, 14.421, 4.672, 12.837, 3.964, 10.71)
      ..lineTo(0.957, 13.042)
      ..cubicTo(2.446, 15.996, 5.57, 18, 9, 18)
      ..close();
    canvas.drawPath(pGreen, green);

    final pYellow = Path()
      ..moveTo(3.964, 10.71)
      ..cubicTo(3.764, 10.117, 3.682, 9.54, 3.682, 9)
      ..cubicTo(3.682, 8.407, 3.784, 7.83, 3.964, 7.29)
      ..lineTo(3.964, 4.958)
      ..lineTo(0.957, 4.958)
      ..cubicTo(0.347, 6.174, 0, 7.548, 0, 9)
      ..cubicTo(0, 10.452, 0.348, 11.827, 0.957, 13.042)
      ..lineTo(3.964, 10.71)
      ..close();
    canvas.drawPath(pYellow, yellow);

    final pRed = Path()
      ..moveTo(9, 3.58)
      ..cubicTo(10.321, 3.58, 11.508, 4.034, 12.44, 4.925)
      ..lineTo(15.022, 2.345)
      ..cubicTo(13.463, 0.891, 11.426, 0, 9, 0)
      ..cubicTo(5.57, 0, 2.446, 2.004, 0.957, 4.958)
      ..lineTo(3.964, 7.29)
      ..cubicTo(4.672, 5.163, 6.656, 3.58, 9, 3.58)
      ..close();
    canvas.drawPath(pRed, red);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

class _GitHubIconPainter extends CustomPainter {
  _GitHubIconPainter(this.color);

  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()..color = color;
    final scale = size.width / 16;
    canvas.scale(scale, scale);
    final path = Path()
      ..moveTo(8, 0)
      ..cubicTo(3.58, 0, 0, 3.58, 0, 8)
      ..cubicTo(0, 11.54, 2.29, 14.53, 5.47, 15.59)
      ..cubicTo(5.87, 15.66, 6.02, 15.42, 6.02, 15.21)
      ..cubicTo(6.02, 15.02, 6.01, 14.39, 6.01, 13.72)
      ..cubicTo(4, 14.09, 3.48, 13.23, 3.31, 12.78)
      ..cubicTo(3.22, 12.55, 2.83, 11.84, 2.18, 11.65)
      ..cubicTo(1.9, 11.5, 1.5, 11.13, 2.17, 11.12)
      ..cubicTo(2.8, 11.11, 3.28, 11.7, 3.43, 11.93)
      ..cubicTo(4.15, 13.14, 5.3, 12.8, 6.06, 12.59)
      ..cubicTo(6.13, 12.07, 6.31, 11.72, 6.51, 11.52)
      ..cubicTo(4.73, 11.32, 2.87, 10.63, 2.87, 7.57)
      ..cubicTo(2.87, 6.7, 3.18, 5.98, 3.69, 5.42)
      ..cubicTo(3.61, 5.22, 3.33, 4.4, 3.77, 3.3)
      ..cubicTo(3.77, 3.3, 4.44, 3.09, 6.02, 4.13)
      ..cubicTo(6.66, 3.95, 7.34, 3.86, 8.02, 3.86)
      ..cubicTo(8.7, 3.86, 9.38, 3.95, 10.02, 4.13)
      ..cubicTo(11.6, 3.09, 12.27, 3.3, 12.27, 3.3)
      ..cubicTo(12.71, 4.4, 12.43, 5.22, 12.35, 5.42)
      ..cubicTo(12.86, 5.98, 13.17, 6.7, 13.17, 7.57)
      ..cubicTo(13.17, 10.64, 11.31, 11.32, 9.53, 11.52)
      ..cubicTo(9.73, 11.72, 9.91, 12.08, 9.91, 12.6)
      ..cubicTo(9.91, 13.37, 9.9, 14.07, 9.9, 14.28)
      ..cubicTo(9.9, 14.49, 10.05, 14.73, 10.45, 14.66)
      ..cubicTo(13.63, 13.6, 16, 10.61, 16, 8)
      ..cubicTo(16, 3.58, 12.42, 0, 8, 0)
      ..close();
    canvas.drawPath(path, paint);
  }

  @override
  bool shouldRepaint(covariant _GitHubIconPainter oldDelegate) =>
      oldDelegate.color != color;
}

class _NotionIconPainter extends CustomPainter {
  _NotionIconPainter(this.color);

  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()..color = color;
    final scale = size.width / 24;
    canvas.scale(scale, scale);
    final path = Path()
      ..moveTo(4.459, 4.208)
      ..cubicTo(5.205, 4.814, 5.485, 4.768, 6.887, 4.674)
      ..lineTo(20.102, 3.881)
      ..cubicTo(20.382, 3.881, 20.149, 3.601, 20.056, 3.555)
      ..lineTo(17.86, 1.968)
      ..cubicTo(17.44, 1.642, 16.88, 1.268, 15.805, 1.361)
      ..lineTo(3.01, 2.295)
      ..cubicTo(2.544, 2.341, 2.45, 2.575, 2.637, 2.761)
      ..close()
      ..moveTo(5.252, 7.428)
      ..lineTo(5.252, 21.332)
      ..cubicTo(5.252, 22.079, 5.625, 22.359, 6.466, 22.312)
      ..lineTo(20.989, 21.472)
      ..cubicTo(21.83, 21.426, 21.924, 20.912, 21.924, 20.305)
      ..lineTo(21.924, 6.354)
      ..cubicTo(21.924, 5.748, 21.691, 5.421, 21.176, 5.467)
      ..lineTo(5.999, 6.354)
      ..cubicTo(5.439, 6.4, 5.252, 6.681, 5.252, 7.287)
      ..close();
    canvas.drawPath(path, paint);
  }

  @override
  bool shouldRepaint(covariant _NotionIconPainter oldDelegate) =>
      oldDelegate.color != color;
}
