import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';

import '../theme/app_theme.dart';

const _fadeDuration = Duration(milliseconds: 300);

/// Ronde knop om tussen licht en donker te wisselen.
class ThemeToggle extends StatelessWidget {
  const ThemeToggle({
    super.key,
    required this.size,
    required this.isDark,
    required this.asset,
    required this.onPressed,
  });

  // De SVG is groter dan de knop: rondom is ruimte gereserveerd voor de schaduw.
  static const _svgInsetX = 12.0;
  static const _svgInsetY = 8.0;

  final double size;
  final bool isDark;

  /// De modus_wissel-SVG die bij [isDark] hoort.
  final String asset;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) {
    final svgSize = size + _svgInsetX * 2;
    return Semantics(
      button: true,
      label: isDark
          ? 'Schakel naar lichte modus'
          : 'Schakel naar donkere modus',
      excludeSemantics: true,
      child: DecoratedBox(
        // flutter_svg negeert SVG-filters, dus de schaduw staat hier.
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          boxShadow: [
            BoxShadow(
              color: context.colors.toggleShadow,
              offset: const Offset(0, 4),
              blurRadius: 12,
            ),
          ],
        ),
        child: SizedBox.square(
          dimension: size,
          child: Stack(
            clipBehavior: Clip.none,
            children: [
              Positioned(
                left: -_svgInsetX,
                top: -_svgInsetY,
                width: svgSize,
                height: svgSize,
                child: AnimatedSwitcher(
                  duration: _fadeDuration,
                  switchInCurve: Curves.easeOut,
                  switchOutCurve: Curves.easeOut,
                  child: SvgPicture.asset(
                    asset,
                    key: ValueKey(isDark),
                    width: svgSize,
                    height: svgSize,
                  ),
                ),
              ),
              Positioned.fill(
                child: Material(
                  type: MaterialType.transparency,
                  shape: const CircleBorder(),
                  clipBehavior: Clip.antiAlias,
                  child: InkWell(onTap: onPressed),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
