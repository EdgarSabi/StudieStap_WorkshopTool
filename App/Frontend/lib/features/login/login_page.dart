import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';

import '../../theme/app_text.dart';
import '../../theme/app_theme.dart';
import '../../widgets/primary_button.dart';
import '../../widgets/theme_toggle.dart';

const _mobileBreakpoint = 800.0;
const _borderWidth = 1.5;
const _mascotAsset = 'assets/login/mascotte_bye.png';

/// Alle decoratie beweegt in één lus van 6 s, zoals in het Figma-prototype.
const _loopDuration = Duration(seconds: 6);

/// Inlogscherm uit de Figma-frames "2. Login" (desktop en mobiel, licht en
/// donker).
class LoginPage extends StatefulWidget {
  const LoginPage({
    super.key,
    required this.onToggleTheme,
    required this.onLogin,
    required this.onForgotPassword,
    required this.onRegister,
  });

  final VoidCallback onToggleTheme;
  final void Function(String email, String password) onLogin;
  final VoidCallback onForgotPassword;
  final VoidCallback onRegister;

  @override
  State<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends State<LoginPage>
    with SingleTickerProviderStateMixin {
  late final AnimationController _loop = AnimationController(
    vsync: this,
    duration: _loopDuration,
  )..repeat();

  late final _motion = _LoginMotion(_loop);
  final _email = TextEditingController();
  final _password = TextEditingController();
  bool _assetsRequested = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (!_assetsRequested) {
      _assetsRequested = true;
      _precacheAssets();
    }
  }

  /// Laadt alle varianten vooraf, zodat wisselen van formaat of thema niet
  /// knippert.
  void _precacheAssets() {
    precacheImage(const AssetImage(_mascotAsset), context);
    final paths = <String>{
      for (final layout in const [_LoginLayout.desktop, _LoginLayout.mobile])
        ...layout.svgAssets,
    };
    for (final path in paths) {
      final loader = SvgAssetLoader(path);
      svg.cache.putIfAbsent(
        loader.cacheKey(null),
        () => loader.loadBytes(null),
      );
    }
  }

  @override
  void dispose() {
    _loop.dispose();
    _email.dispose();
    _password.dispose();
    super.dispose();
  }

  void _submit() {
    widget.onLogin(_email.text.trim(), _password.text);
  }

  @override
  Widget build(BuildContext context) {
    final colors = context.colors;
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Scaffold(
      body: LayoutBuilder(
        builder: (context, constraints) {
          final layout = constraints.maxWidth < _mobileBreakpoint
              ? _LoginLayout.mobile
              : _LoginLayout.desktop;
          final topInset = MediaQuery.paddingOf(context).top;
          final size = Size(
            constraints.maxWidth,
            math.max(constraints.maxHeight, layout.minHeight + topInset),
          );
          final frame = _Frame(layout, size);
          return SingleChildScrollView(
            child: SizedBox.fromSize(
              size: size,
              child: Stack(
                children: [
                  Positioned.fill(
                    child: DecoratedBox(
                      decoration: BoxDecoration(
                        gradient: LinearGradient(
                          begin: Alignment.topCenter,
                          end: Alignment.bottomCenter,
                          colors: [colors.pageTop, colors.pageBottom],
                        ),
                      ),
                    ),
                  ),
                  Positioned.fill(
                    child: IgnorePointer(
                      child: RepaintBoundary(
                        child: _LoginDecor(frame: frame, motion: _motion),
                      ),
                    ),
                  ),
                  Positioned(
                    left: layout.brandLeft,
                    top: layout.brandTop + topInset,
                    child: Text(
                      'AI-coach',
                      style: inter(
                        layout.brandSize,
                        FontWeight.w700,
                        colors.text,
                      ),
                    ),
                  ),
                  Center(
                    child: SizedBox(
                      width: math.min(
                        layout.cardWidth,
                        size.width - layout.sideMargin * 2,
                      ),
                      child: _LoginCard(
                        layout: layout,
                        email: _email,
                        password: _password,
                        onSubmit: _submit,
                        onForgotPassword: widget.onForgotPassword,
                        onRegister: widget.onRegister,
                      ),
                    ),
                  ),
                  _Mascot(frame: frame, motion: _motion),
                  Positioned(
                    top: layout.toggleTop + topInset,
                    right: layout.toggleRight,
                    child: ThemeToggle(
                      size: layout.toggleSize,
                      isDark: isDark,
                      asset: layout.toggleAsset(isDark),
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
}

class _LoginCard extends StatelessWidget {
  const _LoginCard({
    required this.layout,
    required this.email,
    required this.password,
    required this.onSubmit,
    required this.onForgotPassword,
    required this.onRegister,
  });

  final _LoginLayout layout;
  final TextEditingController email;
  final TextEditingController password;
  final VoidCallback onSubmit;
  final VoidCallback onForgotPassword;
  final VoidCallback onRegister;

  @override
  Widget build(BuildContext context) {
    final colors = context.colors;
    return Container(
      padding: layout.cardPadding - const EdgeInsets.all(_borderWidth),
      decoration: BoxDecoration(
        color: colors.card,
        borderRadius: BorderRadius.circular(layout.cardRadius),
        border: Border.all(color: colors.cardBorder, width: _borderWidth),
        boxShadow: [
          BoxShadow(
            color: colors.cardShadow,
            offset: const Offset(0, 6),
            blurRadius: 18,
          ),
        ],
      ),
      child: AutofillGroup(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          spacing: layout.cardGap,
          children: [
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              spacing: 4,
              children: [
                Semantics(
                  header: true,
                  child: Text(
                    'Inloggen',
                    style: inter(
                      layout.titleSize,
                      FontWeight.w700,
                      layout.isCompact
                          ? colors.titleMobile
                          : colors.titleDesktop,
                    ),
                  ),
                ),
                Text(
                  'Log in met je StudieStap-account',
                  style: inter(
                    layout.subtitleSize,
                    FontWeight.w400,
                    colors.textMuted,
                  ),
                ),
              ],
            ),
            _LoginField(
              label: 'E-mailadres',
              hint: 'naam@studiestap.com',
              controller: email,
              keyboardType: TextInputType.emailAddress,
              autofillHints: const [AutofillHints.email],
              textInputAction: TextInputAction.next,
            ),
            _LoginField(
              label: 'Wachtwoord',
              hint: '••••••••',
              controller: password,
              obscureText: true,
              autofillHints: const [AutofillHints.password],
              textInputAction: TextInputAction.done,
              onSubmitted: (_) => onSubmit(),
            ),
            Align(
              alignment: Alignment.centerRight,
              child: _TextLink(
                label: 'Wachtwoord vergeten?',
                style: inter(12, FontWeight.w600, colors.text),
                onPressed: onForgotPassword,
              ),
            ),
            PrimaryButton(
              label: 'Inloggen',
              onPressed: onSubmit,
              padding: layout.buttonPadding,
              radius: layout.buttonRadius,
              fontSize: 14,
            ),
            Center(
              child: _TextLink(
                label: 'Nog geen account? Registreer je',
                style: inter(
                  layout.footerSize,
                  FontWeight.w400,
                  colors.textMuted,
                ),
                onPressed: onRegister,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _LoginField extends StatelessWidget {
  const _LoginField({
    required this.label,
    required this.hint,
    required this.controller,
    required this.autofillHints,
    required this.textInputAction,
    this.keyboardType,
    this.obscureText = false,
    this.onSubmitted,
  });

  final String label;
  final String hint;
  final TextEditingController controller;
  final Iterable<String> autofillHints;
  final TextInputAction textInputAction;
  final TextInputType? keyboardType;
  final bool obscureText;
  final ValueChanged<String>? onSubmitted;

  @override
  Widget build(BuildContext context) {
    final colors = context.colors;
    OutlineInputBorder border(Color color) => OutlineInputBorder(
      borderRadius: BorderRadius.circular(14),
      borderSide: BorderSide(color: color, width: _borderWidth),
    );
    // Samengevoegd zodat schermlezers het label bij het veld voorlezen.
    return MergeSemantics(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        spacing: 6,
        children: [
          Text(label, style: inter(12, FontWeight.w600, colors.text)),
          TextField(
            controller: controller,
            obscureText: obscureText,
            keyboardType: keyboardType,
            autofillHints: autofillHints,
            textInputAction: textInputAction,
            onSubmitted: onSubmitted,
            cursorColor: colors.primary,
            style: inter(13, FontWeight.w400, colors.text),
            decoration: InputDecoration(
              hintText: hint,
              hintStyle: inter(13, FontWeight.w400, colors.inputHint),
              isDense: true,
              filled: true,
              fillColor: colors.inputFill,
              contentPadding: const EdgeInsets.symmetric(
                horizontal: 14 + _borderWidth,
                vertical: 12 + _borderWidth,
              ),
              enabledBorder: border(colors.cardBorder),
              focusedBorder: border(colors.primary),
            ),
          ),
        ],
      ),
    );
  }
}

class _TextLink extends StatelessWidget {
  const _TextLink({
    required this.label,
    required this.style,
    required this.onPressed,
  });

  final String label;
  final TextStyle style;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) {
    return TextButton(
      onPressed: onPressed,
      style: TextButton.styleFrom(
        foregroundColor: style.color,
        padding: EdgeInsets.zero,
        minimumSize: Size.zero,
        tapTargetSize: MaterialTapTargetSize.shrinkWrap,
        textStyle: style,
      ),
      child: Text(label, textAlign: TextAlign.center),
    );
  }
}

// ---------------------------------------------------------------------------
// Decoratie
// ---------------------------------------------------------------------------

/// Keyframes uit het Figma-prototype: vier stappen van 1,5 s, elk ease-in-out.
class _LoginMotion {
  _LoginMotion(AnimationController loop)
    : glow = _keyframes(loop, const [1, 0.6, 1, 0.6, 1]),
      scaleA = _keyframes(loop, const [1, 0.7, 1, 0.7, 1]),
      fadeA = _keyframes(loop, const [1, 0.3, 1, 0.3, 1]),
      scaleB = _keyframes(loop, const [0.7, 1, 0.7, 1, 0.7]),
      fadeB = _keyframes(loop, const [0.3, 1, 0.3, 1, 0.3]),
      mascotTilt = _keyframes(loop, const [-2.5, 0, 2.5, 0, -2.5]),
      mascotLift = _keyframes(loop, const [1, 0, 1, 0, 1]);

  final Animation<double> glow;

  /// Sparkles in fase A beginnen groot, die in fase B klein.
  final Animation<double> scaleA;
  final Animation<double> fadeA;
  final Animation<double> scaleB;
  final Animation<double> fadeB;

  /// Kanteling van de mascotte in graden.
  final Animation<double> mascotTilt;

  /// 1 is helemaal omhoog, 0 is de rustpositie.
  final Animation<double> mascotLift;

  static Animation<double> _keyframes(
    AnimationController loop,
    List<double> values,
  ) {
    return loop.drive(
      TweenSequence([
        for (var i = 0; i < values.length - 1; i++)
          TweenSequenceItem(
            tween: Tween(
              begin: values[i],
              end: values[i + 1],
            ).chain(CurveTween(curve: Curves.easeInOut)),
            weight: 1,
          ),
      ]),
    );
  }
}

/// Zet Figma-coördinaten om naar het scherm. Horizontaal schaalt alles mee met
/// de breedte; verticaal schaalt de desktop mee met de hoogte, terwijl mobiel
/// de vaste afstand tot het midden (en dus tot de kaart) houdt.
class _Frame {
  _Frame(this.layout, this.size)
    : scaleX = size.width / layout.designSize.width,
      scaleY = layout.scalesVertically
          ? size.height / layout.designSize.height
          : 1;

  final _LoginLayout layout;
  final Size size;
  final double scaleX;
  final double scaleY;

  /// Schaal voor objecten die hun verhouding houden.
  double get uniform => math.min(scaleX, scaleY);

  Offset point(Offset design) => Offset(
    design.dx * scaleX,
    size.height / 2 + (design.dy - layout.designSize.height / 2) * scaleY,
  );

  Widget place({
    required Offset center,
    required Size size,
    required Widget child,
  }) {
    final c = point(center);
    return Positioned(
      left: c.dx - size.width / 2,
      top: c.dy - size.height / 2,
      width: size.width,
      height: size.height,
      child: child,
    );
  }
}

class _LoginDecor extends StatelessWidget {
  const _LoginDecor({required this.frame, required this.motion});

  final _Frame frame;
  final _LoginMotion motion;

  @override
  Widget build(BuildContext context) {
    final layout = frame.layout;
    final u = frame.uniform;
    final colors = context.colors;
    return Stack(
      clipBehavior: Clip.none,
      children: [
        for (final glow in layout.glows)
          frame.place(
            center: glow.center,
            size: Size(
              glow.size.width * frame.scaleX,
              glow.size.height * frame.scaleY,
            ),
            child: FadeTransition(
              opacity: motion.glow,
              child: SvgPicture.asset(
                layout.svgPath(glow.asset),
                fit: BoxFit.fill,
              ),
            ),
          ),
        for (final stack in layout.bookStacks)
          frame.place(
            center: stack.center,
            size: stack.size * stack.scale * u,
            child: Transform.rotate(
              angle: stack.rotation * math.pi / 180,
              child: _BookStack(
                spec: stack,
                unit: stack.scale * u,
                colors: colors,
              ),
            ),
          ),
        for (final sparkle in layout.sparkles)
          frame.place(
            center: sparkle.center,
            size: Size.square(sparkle.size * u),
            child: FadeTransition(
              opacity: sparkle.startsLarge ? motion.fadeA : motion.fadeB,
              child: ScaleTransition(
                scale: sparkle.startsLarge ? motion.scaleA : motion.scaleB,
                child: SvgPicture.asset(
                  layout.svgPath(sparkle.asset),
                  width: sparkle.size * u,
                  height: sparkle.size * u,
                ),
              ),
            ),
          ),
        frame.place(
          center: layout.starCenter,
          size: Size.square(layout.starBox * u),
          child: Transform.rotate(
            angle: 10 * math.pi / 180,
            child: FadeTransition(
              opacity: motion.fadeA,
              child: ScaleTransition(
                scale: motion.scaleA,
                child: _Star(
                  asset: layout.svgPath('ster'),
                  box: layout.starBox * u,
                ),
              ),
            ),
          ),
        ),
      ],
    );
  }
}

/// De ster-SVG zit in Figma met een vaste marge in een vierkant vak.
class _Star extends StatelessWidget {
  const _Star({required this.asset, required this.box});

  final String asset;
  final double box;

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        Positioned(
          left: box * 0.1622,
          top: box * 0.1511,
          width: box * (1 - 0.1622 * 2),
          height: box * (1 - 0.1511 - 0.1946),
          child: SvgPicture.asset(asset, fit: BoxFit.fill),
        ),
      ],
    );
  }
}

class _Mascot extends StatelessWidget {
  const _Mascot({required this.frame, required this.motion});

  final _Frame frame;
  final _LoginMotion motion;

  @override
  Widget build(BuildContext context) {
    final layout = frame.layout;
    final u = frame.uniform;
    return frame.place(
      center: layout.mascotCenter,
      size: layout.mascotSize * u,
      child: IgnorePointer(
        child: AnimatedBuilder(
          animation: motion.mascotLift,
          builder: (context, child) => Transform.translate(
            offset: Offset(0, -layout.mascotLift * u * motion.mascotLift.value),
            child: Transform.rotate(
              angle: motion.mascotTilt.value * math.pi / 180,
              child: child,
            ),
          ),
          child: Image.asset(
            _mascotAsset,
            fit: BoxFit.cover,
            excludeFromSemantics: true,
          ),
        ),
      ),
    );
  }
}

enum _BookColor {
  green,
  yellow,
  darkGreen,
  coral,
  lightGreen,
  pink,
  orange,
  lime,
}

extension on _BookColor {
  Color resolve(AppColors colors) => switch (this) {
    _BookColor.green => const Color(0xFF43A047),
    _BookColor.yellow => const Color(0xFFFFC93C),
    _BookColor.darkGreen => const Color(0xFF2E7D32),
    _BookColor.coral => colors.bookCoral,
    _BookColor.lightGreen => colors.bookLightGreen,
    _BookColor.pink => colors.bookPink,
    _BookColor.orange => colors.bookOrange,
    _BookColor.lime => colors.bookLime,
  };
}

/// Eén boek in een stapel, in Figma-eenheden van een stapel op schaal 1.
class _Book {
  const _Book(this.left, this.width, this.color);

  final double left;
  final double width;
  final _BookColor color;
}

class _BookStackSpec {
  const _BookStackSpec({
    required this.center,
    required this.rotation,
    required this.books,
    this.scale = 1,
  });

  static const bookHeight = 34.0;
  static const stackWidth = 190.0;

  final Offset center;

  /// Graden, met de klok mee.
  final double rotation;
  final double scale;

  /// Van boven naar beneden.
  final List<_Book> books;

  Size get size => Size(stackWidth, bookHeight * books.length);
}

/// Boekenstapel: elk boek is een gekleurde kaft met lichte bladzijden en een
/// rug aan de linkerkant.
class _BookStack extends StatelessWidget {
  const _BookStack({
    required this.spec,
    required this.unit,
    required this.colors,
  });

  final _BookStackSpec spec;
  final double unit;
  final AppColors colors;

  @override
  Widget build(BuildContext context) {
    return Stack(
      clipBehavior: Clip.none,
      children: [
        // De onderste boeken eerst, zodat het bovenste boek erop ligt.
        for (var i = spec.books.length - 1; i >= 0; i--)
          ..._bookParts(spec.books[i], i),
      ],
    );
  }

  List<Widget> _bookParts(_Book book, int row) {
    final h = _BookStackSpec.bookHeight * unit;
    final left = book.left * unit;
    final width = book.width * unit;
    final top = row * h;
    final cover = book.color.resolve(colors);
    return [
      _block(Rect.fromLTWH(left, top, width, h), cover, h * 0.2),
      _block(
        Rect.fromLTWH(
          left + width * 0.08,
          top + h * 0.22,
          width * 0.86,
          h * 0.56,
        ),
        colors.bookPages,
        h * 0.1,
      ),
      // Rug
      _block(Rect.fromLTWH(left, top, width * 0.1, h), cover, h * 0.2),
    ];
  }

  static Widget _block(Rect rect, Color color, double radius) {
    return Positioned.fromRect(
      rect: rect,
      child: DecoratedBox(
        decoration: BoxDecoration(
          color: color,
          borderRadius: BorderRadius.circular(radius),
        ),
      ),
    );
  }
}

class _Decor {
  const _Decor(this.asset, this.center, this.size);

  final String asset;
  final Offset center;
  final Size size;
}

class _Sparkle {
  const _Sparkle(
    this.asset,
    this.center,
    this.size, {
    this.startsLarge = false,
  });

  final String asset;
  final Offset center;
  final double size;
  final bool startsLarge;
}

/// Maten uit de desktop- en mobiele Figma-frames.
class _LoginLayout {
  const _LoginLayout({
    required this.folder,
    required this.designSize,
    required this.scalesVertically,
    required this.minHeight,
    required this.isCompact,
    required this.glows,
    required this.bookStacks,
    required this.sparkles,
    required this.starCenter,
    required this.starBox,
    required this.mascotCenter,
    required this.mascotSize,
    required this.mascotLift,
    required this.brandLeft,
    required this.brandTop,
    required this.brandSize,
    required this.toggleTop,
    required this.toggleRight,
    required this.toggleSize,
    required this.cardWidth,
    required this.sideMargin,
    required this.cardPadding,
    required this.cardRadius,
    required this.cardGap,
    required this.titleSize,
    required this.subtitleSize,
    required this.buttonPadding,
    required this.buttonRadius,
    required this.footerSize,
  });

  final String folder;
  final Size designSize;
  final bool scalesVertically;

  /// Onder deze hoogte gaat de pagina scrollen, zodat de mascotte niet over
  /// de kop schuift.
  final double minHeight;
  final bool isCompact;
  final List<_Decor> glows;
  final List<_BookStackSpec> bookStacks;
  final List<_Sparkle> sparkles;
  final Offset starCenter;
  final double starBox;
  final Offset mascotCenter;
  final Size mascotSize;

  /// Hoeveel pixels de mascotte omhoog deint.
  final double mascotLift;
  final double brandLeft;
  final double brandTop;
  final double brandSize;
  final double toggleTop;
  final double toggleRight;
  final double toggleSize;
  final double cardWidth;
  final double sideMargin;
  final EdgeInsets cardPadding;
  final double cardRadius;
  final double cardGap;
  final double titleSize;
  final double subtitleSize;
  final EdgeInsets buttonPadding;
  final double buttonRadius;
  final double footerSize;

  String svgPath(String name) => 'assets/login/$folder/$name.svg';

  /// De themaknop is dezelfde als op de landingspagina.
  String toggleAsset(bool isDark) =>
      'assets/landing/$folder/${isDark ? 'dark' : 'light'}/modus_wissel.svg';

  Iterable<String> get svgAssets => [
    for (final glow in glows) svgPath(glow.asset),
    for (final sparkle in sparkles) svgPath(sparkle.asset),
    svgPath('ster'),
    toggleAsset(false),
    toggleAsset(true),
  ];

  static const desktop = _LoginLayout(
    folder: 'desktop',
    designSize: Size(1440, 1024),
    scalesVertically: true,
    minHeight: 640,
    isCompact: false,
    glows: [
      _Decor('gloed_links', Offset(288, 102.4), Size(960, 636)),
      _Decor('gloed_rechts', Offset(1296, 921.6), Size(960, 636)),
    ],
    bookStacks: [
      _BookStackSpec(
        center: Offset(125.81, 825.7),
        rotation: 4,
        books: [
          _Book(-7, 184, _BookColor.darkGreen),
          _Book(11.5, 187, _BookColor.yellow),
          _Book(10, 150, _BookColor.green),
        ],
      ),
      _BookStackSpec(
        center: Offset(1315.97, 216.74),
        rotation: -5,
        books: [
          _Book(14.5, 181, _BookColor.pink),
          _Book(-7, 184, _BookColor.green),
          _Book(11.5, 187, _BookColor.lightGreen),
          _Book(10, 150, _BookColor.coral),
        ],
      ),
      _BookStackSpec(
        center: Offset(1263.12, 880.14),
        rotation: 6,
        books: [
          _Book(11.5, 187, _BookColor.orange),
          _Book(10, 150, _BookColor.darkGreen),
        ],
      ),
      _BookStackSpec(
        center: Offset(175.83, 194.68),
        rotation: -6,
        books: [
          _Book(11.5, 187, _BookColor.coral),
          _Book(10, 150, _BookColor.lime),
        ],
      ),
    ],
    sparkles: [
      _Sparkle('sparkle_1', Offset(574, 264), 28, startsLarge: true),
      _Sparkle('sparkle_2', Offset(895, 765), 30),
      _Sparkle('sparkle_3', Offset(864, 153.6), 20),
      _Sparkle('sparkle_4', Offset(432, 563.2), 22),
    ],
    starCenter: Offset(645.92, 841.42),
    starBox: 22,
    mascotCenter: Offset(192.25, 482.54),
    mascotSize: Size(264.5, 285.08),
    mascotLift: 8,
    brandLeft: 48,
    brandTop: 40,
    brandSize: 16,
    toggleTop: 16,
    toggleRight: 16,
    toggleSize: 44,
    cardWidth: 440,
    sideMargin: 24,
    cardPadding: EdgeInsets.all(48),
    cardRadius: 22,
    cardGap: 20,
    titleSize: 24,
    subtitleSize: 13,
    buttonPadding: EdgeInsets.symmetric(horizontal: 20, vertical: 14),
    buttonRadius: 22.5,
    footerSize: 13,
  );

  static const mobile = _LoginLayout(
    folder: 'mobile',
    designSize: Size(390, 844),
    scalesVertically: false,
    minHeight: 760,
    isCompact: true,
    glows: [
      _Decor('gloed_links', Offset(78, 84.4), Size(324, 596.4)),
      _Decor('gloed_rechts', Offset(351, 759.6), Size(324, 596.4)),
    ],
    bookStacks: [
      _BookStackSpec(
        center: Offset(31.55, 681.3),
        rotation: 4,
        scale: 0.9378,
        books: [
          _Book(-7, 184, _BookColor.darkGreen),
          _Book(11.5, 187, _BookColor.yellow),
          _Book(10, 150, _BookColor.green),
        ],
      ),
      _BookStackSpec(
        center: Offset(304.31, 145.76),
        rotation: -5,
        scale: 0.9378,
        books: [
          _Book(14.5, 181, _BookColor.pink),
          _Book(-7, 184, _BookColor.green),
          _Book(11.5, 187, _BookColor.lightGreen),
          _Book(10, 150, _BookColor.coral),
        ],
      ),
      _BookStackSpec(
        center: Offset(308.95, 766.91),
        rotation: 6,
        scale: 0.75,
        books: [
          _Book(11.5, 187, _BookColor.orange),
          _Book(10, 150, _BookColor.darkGreen),
        ],
      ),
    ],
    sparkles: [
      _Sparkle('sparkle_1', Offset(153.13, 203.13), 26.258, startsLarge: true),
      _Sparkle('sparkle_2', Offset(244.07, 644.07), 28.133),
      _Sparkle('sparkle_3', Offset(189.38, 129.38), 18.756),
      _Sparkle('sparkle_4', Offset(120.32, 640.32), 20.631),
    ],
    starCenter: Offset(173.55, 693.71),
    starBox: 20.631,
    mascotCenter: Offset(80, 164.67),
    mascotSize: Size(120, 129.34),
    mascotLift: 5.6,
    brandLeft: 20,
    brandTop: 24,
    brandSize: 15,
    toggleTop: 14,
    toggleRight: 16,
    toggleSize: 36,
    cardWidth: 342,
    sideMargin: 16,
    cardPadding: EdgeInsets.symmetric(horizontal: 28, vertical: 32),
    cardRadius: 20,
    cardGap: 18,
    titleSize: 20,
    subtitleSize: 12,
    buttonPadding: EdgeInsets.symmetric(horizontal: 20, vertical: 13),
    buttonRadius: 21.5,
    footerSize: 12,
  );
}
