import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';

import '../../theme/app_theme.dart';
import 'landing_scene.dart';
import 'landing_scene_data.dart';

const _themeFadeDuration = Duration(milliseconds: 300);
const _mobileBreakpoint = 800.0;
const _cardBorderWidth = 1.5;
const _mascotAsset = 'assets/landing/mascotte_yay.png';

/// Tekststijl uit Figma: regelhoogte "normal" van Inter, zonder de regelhoogte
/// en letterafstand die Material anders meegeeft.
TextStyle _inter(
  double size,
  FontWeight weight,
  Color color, {
  double spacing = 0,
}) {
  return TextStyle(
    fontFamily: 'Inter',
    fontSize: size,
    fontWeight: weight,
    color: color,
    height: 1.21,
    letterSpacing: spacing,
  );
}

class LandingPage extends StatefulWidget {
  const LandingPage({
    super.key,
    required this.isDark,
    required this.onToggleTheme,
    required this.onLogin,
    required this.onRegister,
  });

  final bool isDark;
  final VoidCallback onToggleTheme;
  final VoidCallback onLogin;
  final VoidCallback onRegister;

  @override
  State<LandingPage> createState() => _LandingPageState();
}

class _LandingPageState extends State<LandingPage>
    with SingleTickerProviderStateMixin {
  late final AnimationController _loop = AnimationController(
    vsync: this,
    duration: sceneLoopDuration,
  )..repeat();
  bool _assetsRequested = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (!_assetsRequested) {
      _assetsRequested = true;
      _precacheAssets();
    }
  }

  /// Laadt alle varianten vooraf, zodat de themawissel niet knippert.
  void _precacheAssets() {
    precacheImage(const AssetImage(_mascotAsset), context);
    for (final layout in const [_LayoutSpec.desktop, _LayoutSpec.mobile]) {
      for (final isDark in const [false, true]) {
        final names = {
          ...layout.layers.map((layer) => layer.asset),
          'modus_wissel',
        };
        for (final name in names) {
          final loader = SvgAssetLoader(layout.svgPath(name, isDark));
          svg.cache.putIfAbsent(
            loader.cacheKey(null),
            () => loader.loadBytes(null),
          );
        }
      }
    }
  }

  @override
  void dispose() {
    _loop.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final colors = context.colors;
    return Scaffold(
      body: LayoutBuilder(
        builder: (context, constraints) {
          final layout = constraints.maxWidth < _mobileBreakpoint
              ? _LayoutSpec.mobile
              : _LayoutSpec.desktop;
          final topInset = MediaQuery.paddingOf(context).top;
          return SingleChildScrollView(
            child: ConstrainedBox(
              constraints: BoxConstraints(minHeight: constraints.maxHeight),
              child: Stack(
                children: [
                  Positioned.fill(
                    child: DecoratedBox(
                      decoration: BoxDecoration(
                        gradient: LinearGradient(
                          begin: Alignment.topCenter,
                          end: Alignment.bottomCenter,
                          colors: [colors.skyTop, colors.skyBottom],
                        ),
                      ),
                    ),
                  ),
                  Positioned.fill(child: _buildScene(layout)),
                  Padding(
                    padding: EdgeInsets.only(
                      top: topInset,
                      bottom: layout.groundReserve,
                    ),
                    child: _LandingContent(
                      layout: layout,
                      onLogin: widget.onLogin,
                      onRegister: widget.onRegister,
                    ),
                  ),
                  Positioned.fill(
                    child: IgnorePointer(
                      child: RepaintBoundary(
                        child: SceneStage(
                          designSize: layout.designSize,
                          layers: [layout.mascot],
                          animation: _loop,
                          layerBuilder: (_) => Image.asset(
                            _mascotAsset,
                            fit: BoxFit.cover,
                            excludeFromSemantics: true,
                          ),
                        ),
                      ),
                    ),
                  ),
                  Positioned(
                    top: layout.toggleTop + topInset,
                    right: layout.toggleRight,
                    child: _ThemeToggle(
                      layout: layout,
                      isDark: widget.isDark,
                      onPressed: widget.onToggleTheme,
                    ),
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }

  Widget _buildScene(_LayoutSpec layout) {
    return IgnorePointer(
      child: RepaintBoundary(
        child: AnimatedSwitcher(
          duration: _themeFadeDuration,
          switchInCurve: Curves.easeOut,
          switchOutCurve: Curves.easeOut,
          layoutBuilder: (current, previous) =>
              Stack(fit: StackFit.expand, children: [...previous, ?current]),
          child: SceneStage(
            key: ValueKey('${layout.folder}-${widget.isDark}'),
            designSize: layout.designSize,
            layers: layout.layers,
            animation: _loop,
            layerBuilder: (layer) => SvgPicture.asset(
              layout.svgPath(layer.asset, widget.isDark),
              fit: BoxFit.fill,
            ),
          ),
        ),
      ),
    );
  }
}

/// Maten uit de desktop- en mobiele Figma-frames.
class _LayoutSpec {
  const _LayoutSpec({
    required this.folder,
    required this.designSize,
    required this.layers,
    required this.mascot,
    required this.isCompact,
    required this.groundReserve,
    required this.toggleTop,
    required this.toggleRight,
    required this.toggleSize,
    required this.navPadding,
    required this.navGap,
    required this.brandSize,
    required this.navTextSize,
    required this.navButtonPadding,
    required this.navButtonRadius,
    required this.heroPadding,
    required this.heroGap,
    required this.eyebrowSize,
    required this.eyebrowSpacing,
    required this.titleSize,
    required this.titleWidth,
    required this.introSize,
    required this.introWidth,
    required this.intro,
    required this.ctaPadding,
    required this.ctaRadius,
    required this.ctaTextSize,
    required this.benefitsPadding,
    required this.benefitsGap,
    required this.cardPadding,
    required this.cardGap,
    required this.cardTitleSize,
    required this.cardBodySize,
  });

  final String folder;
  final Size designSize;
  final List<SceneLayer> layers;
  final SceneLayer mascot;
  final bool isCompact;

  /// Ruimte onder de inhoud waarin het landschap en de mascotte zichtbaar zijn.
  final double groundReserve;
  final double toggleTop;
  final double toggleRight;
  final double toggleSize;
  final EdgeInsets navPadding;
  final double navGap;
  final double brandSize;
  final double navTextSize;
  final EdgeInsets navButtonPadding;
  final double navButtonRadius;
  final EdgeInsets heroPadding;
  final double heroGap;
  final double eyebrowSize;
  final double eyebrowSpacing;
  final double titleSize;
  final double titleWidth;
  final double introSize;
  final double introWidth;
  final String intro;
  final EdgeInsets ctaPadding;
  final double ctaRadius;
  final double ctaTextSize;
  final EdgeInsets benefitsPadding;
  final double benefitsGap;
  final double cardPadding;
  final double cardGap;
  final double cardTitleSize;
  final double cardBodySize;

  String svgPath(String name, bool isDark) =>
      'assets/landing/$folder/${isDark ? 'dark' : 'light'}/$name.svg';

  static const desktop = _LayoutSpec(
    folder: 'desktop',
    designSize: Size(1440, 1024),
    layers: desktopSceneLayers,
    mascot: desktopMascot,
    isCompact: false,
    groundReserve: 375,
    toggleTop: 96,
    toggleRight: 16,
    toggleSize: 44,
    navPadding: EdgeInsets.symmetric(horizontal: 48, vertical: 24),
    navGap: 11,
    brandSize: 16,
    navTextSize: 13,
    navButtonPadding: EdgeInsets.symmetric(horizontal: 18, vertical: 10),
    navButtonRadius: 18,
    heroPadding: EdgeInsets.fromLTRB(48, 80, 48, 56),
    heroGap: 20,
    eyebrowSize: 12,
    eyebrowSpacing: 0.48,
    titleSize: 34,
    titleWidth: 680,
    introSize: 15,
    introWidth: 520,
    intro:
        'De AI-coach luistert je workshop terug en geeft je na afloop concrete '
        'feedback, zodat je blijft groeien als StudieStapper.',
    ctaPadding: EdgeInsets.symmetric(horizontal: 32, vertical: 16),
    ctaRadius: 25,
    ctaTextSize: 15,
    benefitsPadding: EdgeInsets.fromLTRB(48, 0, 48, 80),
    benefitsGap: 24,
    cardPadding: 24,
    cardGap: 8,
    cardTitleSize: 15,
    cardBodySize: 13,
  );

  static const mobile = _LayoutSpec(
    folder: 'mobile',
    designSize: Size(390, 844),
    layers: mobileSceneLayers,
    mascot: mobileMascot,
    isCompact: true,
    groundReserve: 188,
    toggleTop: 72,
    toggleRight: 14,
    toggleSize: 36,
    navPadding: EdgeInsets.fromLTRB(20, 20, 20, 16),
    navGap: 10,
    brandSize: 14,
    navTextSize: 11,
    navButtonPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 7),
    navButtonRadius: 13.5,
    heroPadding: EdgeInsets.fromLTRB(24, 24, 24, 32),
    heroGap: 16,
    eyebrowSize: 10,
    eyebrowSpacing: 0.3,
    titleSize: 22,
    titleWidth: 320,
    introSize: 13,
    introWidth: 300,
    intro:
        'De AI-coach luistert je workshop terug en geeft je na afloop concrete '
        'feedback.',
    ctaPadding: EdgeInsets.symmetric(horizontal: 20, vertical: 14),
    ctaRadius: 22,
    ctaTextSize: 13,
    benefitsPadding: EdgeInsets.fromLTRB(20, 0, 20, 32),
    benefitsGap: 12,
    cardPadding: 18,
    cardGap: 6,
    cardTitleSize: 13,
    cardBodySize: 12,
  );
}

const _benefits = [
  (
    title: 'Automatische feedback',
    body: "Geen extra werk voor collega's — de AI-coach luistert de opname terug.",
  ),
  (
    title: 'Vier heldere indicatoren',
    body: 'Vraaggedrag, begripscontrole, reageren op antwoorden en interactie.',
  ),
  (
    title: 'Altijd transparant',
    body:
        'Je ziet precies hoe de feedback tot stand komt en wat er met je opname '
        'gebeurt.',
  ),
];

class _LandingContent extends StatelessWidget {
  const _LandingContent({
    required this.layout,
    required this.onLogin,
    required this.onRegister,
  });

  final _LayoutSpec layout;
  final VoidCallback onLogin;
  final VoidCallback onRegister;

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [_buildNav(context), _buildHero(context), _buildBenefits()],
    );
  }

  Widget _buildNav(BuildContext context) {
    final colors = context.colors;
    return Padding(
      padding: layout.navPadding,
      child: Row(
        children: [
          Expanded(
            child: Text(
              'AI-coach',
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: _inter(layout.brandSize, FontWeight.w700, colors.text),
            ),
          ),
          TextButton(
            onPressed: onLogin,
            style: TextButton.styleFrom(
              foregroundColor: colors.text,
              padding: EdgeInsets.zero,
              minimumSize: Size.zero,
              tapTargetSize: MaterialTapTargetSize.shrinkWrap,
              textStyle: _inter(
                layout.navTextSize,
                FontWeight.w600,
                colors.text,
              ),
            ),
            child: const Text('Inloggen'),
          ),
          SizedBox(width: layout.navGap),
          _PrimaryButton(
            label: 'Registreren',
            onPressed: onRegister,
            padding: layout.navButtonPadding,
            radius: layout.navButtonRadius,
            fontSize: layout.navTextSize,
          ),
        ],
      ),
    );
  }

  Widget _buildHero(BuildContext context) {
    final colors = context.colors;
    final cta = _PrimaryButton(
      label: 'Registreer je account →',
      onPressed: onRegister,
      padding: layout.ctaPadding,
      radius: layout.ctaRadius,
      fontSize: layout.ctaTextSize,
    );
    return Padding(
      padding: layout.heroPadding,
      child: Column(
        spacing: layout.heroGap,
        children: [
          Text(
            'VOOR STUDIESTAPPERS',
            textAlign: TextAlign.center,
            style: _inter(
              layout.eyebrowSize,
              FontWeight.w600,
              colors.textMuted,
              spacing: layout.eyebrowSpacing,
            ),
          ),
          ConstrainedBox(
            constraints: BoxConstraints(maxWidth: layout.titleWidth),
            child: Text(
              'Feedback op je workshop, zonder dat iemand hoeft mee te kijken',
              textAlign: TextAlign.center,
              style: _inter(
                layout.titleSize,
                FontWeight.w700,
                layout.isCompact ? colors.titleMobile : colors.titleDesktop,
              ),
            ),
          ),
          ConstrainedBox(
            constraints: BoxConstraints(maxWidth: layout.introWidth),
            child: Text(
              layout.intro,
              textAlign: TextAlign.center,
              style: _inter(
                layout.introSize,
                FontWeight.w400,
                colors.textMuted,
              ),
            ),
          ),
          if (layout.isCompact)
            SizedBox(width: double.infinity, child: cta)
          else
            cta,
        ],
      ),
    );
  }

  Widget _buildBenefits() {
    final cards = [
      for (final benefit in _benefits)
        _BenefitCard(title: benefit.title, body: benefit.body, layout: layout),
    ];
    return Padding(
      padding: layout.benefitsPadding,
      child: layout.isCompact
          ? Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              spacing: layout.benefitsGap,
              children: cards,
            )
          : Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              spacing: layout.benefitsGap,
              children: [for (final card in cards) Expanded(child: card)],
            ),
    );
  }
}

class _PrimaryButton extends StatelessWidget {
  const _PrimaryButton({
    required this.label,
    required this.onPressed,
    required this.padding,
    required this.radius,
    required this.fontSize,
  });

  final String label;
  final VoidCallback onPressed;
  final EdgeInsets padding;
  final double radius;
  final double fontSize;

  @override
  Widget build(BuildContext context) {
    final colors = context.colors;
    final borderRadius = BorderRadius.circular(radius);
    return DecoratedBox(
      decoration: BoxDecoration(
        borderRadius: borderRadius,
        boxShadow: [
          BoxShadow(
            color: colors.primaryShadow,
            offset: const Offset(0, 4),
            blurRadius: 10,
          ),
        ],
      ),
      child: Material(
        color: colors.primary,
        borderRadius: borderRadius,
        clipBehavior: Clip.antiAlias,
        child: InkWell(
          onTap: onPressed,
          child: Padding(
            padding: padding,
            child: Text(
              label,
              textAlign: TextAlign.center,
              style: _inter(fontSize, FontWeight.w600, Colors.white),
            ),
          ),
        ),
      ),
    );
  }
}

class _BenefitCard extends StatelessWidget {
  const _BenefitCard({
    required this.title,
    required this.body,
    required this.layout,
  });

  final String title;
  final String body;
  final _LayoutSpec layout;

  @override
  Widget build(BuildContext context) {
    final colors = context.colors;
    return Container(
      padding: EdgeInsets.all(layout.cardPadding - _cardBorderWidth),
      decoration: BoxDecoration(
        color: colors.card,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: colors.cardBorder, width: _cardBorderWidth),
        boxShadow: [
          BoxShadow(
            color: colors.cardShadow,
            offset: const Offset(0, 6),
            blurRadius: 18,
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        spacing: layout.cardGap,
        children: [
          Text(
            title,
            style: _inter(layout.cardTitleSize, FontWeight.w600, colors.text),
          ),
          Text(
            body,
            style: _inter(
              layout.cardBodySize,
              FontWeight.w400,
              colors.textMuted,
            ),
          ),
        ],
      ),
    );
  }
}

class _ThemeToggle extends StatelessWidget {
  const _ThemeToggle({
    required this.layout,
    required this.isDark,
    required this.onPressed,
  });

  // De SVG is groter dan de knop: rondom is ruimte gereserveerd voor de schaduw.
  static const _svgInsetX = 12.0;
  static const _svgInsetY = 8.0;

  final _LayoutSpec layout;
  final bool isDark;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) {
    final size = layout.toggleSize;
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
                  duration: _themeFadeDuration,
                  switchInCurve: Curves.easeOut,
                  switchOutCurve: Curves.easeOut,
                  child: SvgPicture.asset(
                    layout.svgPath('modus_wissel', isDark),
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
