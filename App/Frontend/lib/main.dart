import 'package:flutter/material.dart';

import 'features/landing/landing_page.dart';
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
  bool _isDark = false;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'AI-coach',
      debugShowCheckedModeBanner: false,
      theme: lightTheme,
      darkTheme: darkTheme,
      themeMode: _isDark ? ThemeMode.dark : ThemeMode.light,
      themeAnimationDuration: const Duration(milliseconds: 300),
      themeAnimationCurve: Curves.easeOut,
      home: LandingPage(
        isDark: _isDark,
        onToggleTheme: () => setState(() => _isDark = !_isDark),
        // De login- en registratieschermen bestaan nog niet.
        onLogin: () {},
        onRegister: () {},
      ),
    );
  }
}
