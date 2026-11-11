import 'package:flutter/material.dart';

import 'features/landing/landing_page.dart';
import 'features/login/login_page.dart';
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

  void _openLogin() {
    _navigator.currentState!.push(
      MaterialPageRoute<void>(
        builder: (_) => LoginPage(
          onToggleTheme: _toggleTheme,
          // Er is nog geen backend, en de schermen voor wachtwoord vergeten
          // en registreren bestaan nog niet.
          onLogin: (email, password) {},
          onForgotPassword: () {},
          onRegister: () {},
        ),
      ),
    );
  }

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
        // Het registratiescherm bestaat nog niet.
        onRegister: () {},
      ),
    );
  }
}
