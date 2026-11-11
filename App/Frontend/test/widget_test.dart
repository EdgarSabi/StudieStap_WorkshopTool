import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:stapper_coach/features/landing/landing_page.dart';
import 'package:stapper_coach/features/landing/landing_scene.dart';
import 'package:stapper_coach/main.dart';
import 'package:stapper_coach/theme/app_theme.dart';

void main() {
  void setScreen(WidgetTester tester, Size size) {
    tester.view.physicalSize = size;
    tester.view.devicePixelRatio = 1;
    tester.platformDispatcher.accessibilityFeaturesTestValue =
        const FakeAccessibilityFeatures(disableAnimations: true);
    addTearDown(tester.view.reset);
    addTearDown(tester.platformDispatcher.clearAccessibilityFeaturesTestValue);
  }

  Widget page({VoidCallback? onLogin, VoidCallback? onRegister}) => MaterialApp(
    theme: lightTheme,
    home: LandingPage(
      isDark: false,
      onToggleTheme: () {},
      onLogin: onLogin ?? () {},
      onRegister: onRegister ?? () {},
    ),
  );

  group('SceneLayer', () {
    const layer = SceneLayer('sparkle_01', 10, 10, [
      Pose(0, 0, 0, 0.75),
      Pose(40, 0, 0, 0.375),
      Pose(80, 0, 0, 0.75),
      Pose(120, 0, 0, 0.75),
    ]);

    test('staat op elk kwart van de lus precies op een keyframe', () {
      expect(layer.poseAt(0).x, 0);
      expect(layer.poseAt(0.25).x, 40);
      expect(layer.poseAt(0.5).x, 80);
      expect(layer.poseAt(0.75).x, 120);
    });

    test('wacht 0,1 s en is halverwege de overgang op het midden', () {
      expect(layer.poseAt(0.05 / sceneStepSeconds / 4).x, 0);
      final halfway = (0.1 + 1.5) / sceneStepSeconds / 4;
      expect(layer.poseAt(halfway).x, closeTo(20, 0.01));
    });

    test('loopt vanaf het laatste keyframe terug naar het eerste', () {
      final halfway = 0.75 + (0.1 + 1.5) / sceneStepSeconds / 4;
      expect(layer.poseAt(halfway).x, closeTo(60, 0.01));
    });

    test('past opacity die al in de SVG zit niet dubbel toe', () {
      expect(layer.relativeOpacity(layer.poses[0]), 1);
      expect(layer.relativeOpacity(layer.poses[1]), 0.5);
      const cloud = SceneLayer('wolk_1', 10, 10, [Pose(0, 0, 0, 0.92)]);
      expect(cloud.relativeOpacity(cloud.poses.first), 0.92);
    });
  });

  group('driftedLeft', () {
    double left(double seconds) => driftedLeft(
      startLeft: 900,
      width: 100,
      screenWidth: 1000,
      crossingSeconds: 100,
      elapsedSeconds: seconds,
    );

    test('begint op de positie uit het ontwerp', () {
      expect(left(0), 900);
    });

    test('schuift langzaam naar links', () {
      expect(left(10), closeTo(800, 1e-9));
    });

    test('komt rechts terug zodra hij links helemaal uit beeld is', () {
      expect(left(100), closeTo(-100, 1e-9));
      expect(left(101), closeTo(990, 1e-9));
    });
  });

  testWidgets('desktop toont de teksten uit het ontwerp', (tester) async {
    setScreen(tester, const Size(1440, 1024));
    await tester.pumpWidget(page());

    expect(find.text('VOOR STUDIESTAPPERS'), findsOneWidget);
    expect(
      find.textContaining('zodat je blijft groeien als StudieStapper'),
      findsOneWidget,
    );
    expect(find.text('Vier heldere indicatoren'), findsOneWidget);
  });

  testWidgets('mobiel toont de kortere intro', (tester) async {
    setScreen(tester, const Size(390, 844));
    await tester.pumpWidget(page());

    expect(find.textContaining('concrete feedback.'), findsOneWidget);
    expect(find.textContaining('blijft groeien'), findsNothing);
  });

  testWidgets('knoppen roepen de juiste acties aan', (tester) async {
    setScreen(tester, const Size(1440, 1024));
    var logins = 0;
    var registrations = 0;
    await tester.pumpWidget(
      page(onLogin: () => logins++, onRegister: () => registrations++),
    );

    await tester.tap(find.text('Inloggen'));
    await tester.tap(find.text('Registreren'));
    await tester.tap(find.text('Registreer je account →'));

    expect(logins, 1);
    expect(registrations, 2);
  });

  testWidgets('de themaknop wisselt tussen licht en donker', (tester) async {
    setScreen(tester, const Size(1440, 1024));
    await tester.pumpWidget(const StapperCoachApp());

    await tester.tap(find.bySemanticsLabel('Schakel naar donkere modus'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 400));

    expect(find.bySemanticsLabel('Schakel naar lichte modus'), findsOneWidget);
    final context = tester.element(find.text('AI-coach'));
    expect(context.colors.text, AppColors.dark.text);
  });

  testWidgets('de achtergrond beweegt ook als animaties uit staan in het OS', (
    tester,
  ) async {
    setScreen(tester, const Size(1440, 1024));
    List<String> transforms() => tester
        .widgetList<Transform>(find.byType(Transform))
        .map((widget) => widget.transform.storage.toString())
        .toList();

    await tester.pumpWidget(page());
    final start = transforms();
    await tester.pump(const Duration(milliseconds: 3100));

    expect(transforms(), isNot(start));
  });

  for (final size in const [
    Size(320, 568),
    Size(390, 844),
    Size(799, 600),
    Size(800, 600),
    Size(1440, 1024),
    Size(2560, 1440),
  ]) {
    testWidgets('geen layoutfouten op ${size.width}x${size.height}', (
      tester,
    ) async {
      setScreen(tester, size);
      await tester.pumpWidget(page());

      expect(tester.takeException(), isNull);
    });
  }
}
