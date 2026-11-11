import 'package:flutter/material.dart';

import 'features/forgot_password/forgot_password_page.dart';
import 'features/landing/landing_page.dart';
import 'features/login/login_page.dart';
import 'features/register/register_page.dart';
import 'theme/app_theme.dart';

void main() {
  runApp(const StapperCoachApp());
}

class StapperCoachApp extends StatefulWidget {
  const StapperCoachApp({super.key});

  @override
  State<StapperCoachApp> createState() => _StapperCoachAppState();
}

class _StapperCoachAppState extends State<StapperCoachApp> {
  final _navigator = GlobalKey<NavigatorState>();
  bool _isDark = false;

  void _toggleTheme() => setState(() => _isDark = !_isDark);

  NavigatorState get _nav => _navigator.currentState!;

  /// Opent [page]. Met [replace] vervangt het het huidige scherm, zodat heen
  /// en weer wisselen tussen inloggen en registreren de stapel niet laat
  /// groeien en "terug" naar de landingspagina gaat.
  void _open(Widget page, {bool replace = false}) {
    final route = MaterialPageRoute<void>(builder: (_) => page);
    if (replace) {
      _nav.pushReplacement(route);
    } else {
      _nav.push(route);
    }
  }

  // De backend bestaat nog niet, dus inloggen, registreren en de reset-link
  // versturen doen nog niets.

  void _openLogin({bool replace = false}) => _open(
    LoginPage(
      onToggleTheme: _toggleTheme,
      onLogin: (email, password) {},
      onForgotPassword: _openForgotPassword,
      onRegister: () => _openRegister(replace: true),
    ),
    replace: replace,
  );

  void _openRegister({bool replace = false}) => _open(
    RegisterPage(
      onToggleTheme: _toggleTheme,
      onRegister: (name, email, password) {},
      onLogin: () => _openLogin(replace: true),
    ),
    replace: replace,
  );

  void _openForgotPassword() => _open(
    ForgotPasswordPage(
      onToggleTheme: _toggleTheme,
      onSendResetLink: (email) {},
      // Dit scherm wordt altijd vanaf het loginscherm geopend.
      onBackToLogin: _nav.pop,
    ),
  );

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'AI-coach',
      debugShowCheckedModeBanner: false,
      navigatorKey: _navigator,
      theme: lightTheme,
      darkTheme: darkTheme,
      themeMode: _isDark ? ThemeMode.dark : ThemeMode.light,
      themeAnimationDuration: const Duration(milliseconds: 300),
      themeAnimationCurve: Curves.easeOut,
      home: LandingPage(
        isDark: _isDark,
        onToggleTheme: _toggleTheme,
        onLogin: _openLogin,
        onRegister: _openRegister,
      ),
    );
  }
}
