import 'dart:math' as math;

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

/// Eén keyframe van een laag, in Figma-coördinaten (middelpunt van de laag).
class Pose {
  const Pose(this.x, this.y, this.rotation, this.opacity);

  final double x;
  final double y;

  /// Rotatie in graden, met de klok mee.
  final double rotation;
  final double opacity;

  static Pose lerp(Pose a, Pose b, double t) => Pose(
    a.x + (b.x - a.x) * t,
    a.y + (b.y - a.y) * t,
    a.rotation + (b.rotation - a.rotation) * t,
    a.opacity + (b.opacity - a.opacity) * t,
  );
}

/// Een decoratieve laag uit de Figma-scène.
class SceneLayer {
  const SceneLayer(
    this.asset,
    this.width,
    this.height,
    this.poses, {
    this.stretch = false,
    this.driftSeconds,
  });

  final String asset;
  final double width;
  final double height;

  /// Eén pose betekent een statische laag, vier poses een geanimeerde laag.
  final List<Pose> poses;

  /// Landschapslagen rekken mee met het scherm, objecten houden hun verhouding.
  final bool stretch;

  /// Als dit is ingesteld, drijft de laag van rechts naar links en doet hij
  /// er zoveel seconden over om één schermbreedte af te leggen. De
  /// horizontale beweging uit de keyframes vervalt dan; het deinen blijft.
  final double? driftSeconds;

  bool get isAnimated => poses.length > 1;
  bool get drifts => driftSeconds != null;

  /// De Figma-export heeft de opacity van het eerste frame al in de SVG zitten,
  /// behalve bij wolken: daar staat die op het omliggende frame.
  double get _opacityInAsset =>
      asset.startsWith('wolk') ? 1 : poses.first.opacity;

  double relativeOpacity(Pose pose) => pose.opacity / _opacityInAsset;

  /// Pose op [t] (0..1) in de lus, volgens het Figma-prototype: elke stap
  /// wacht 0,1 s en animeert daarna 3 s met ease-in-out.
  Pose poseAt(double t) {
    if (!isAnimated) return poses.first;
    final position = t * poses.length;
    final index = position.floor() % poses.length;
    final stepSeconds = (position - position.floor()) * sceneStepSeconds;
    final progress =
        ((stepSeconds - sceneDelaySeconds) / sceneTransitionSeconds).clamp(
          0.0,
          1.0,
        );
    return Pose.lerp(
      poses[index],
      poses[(index + 1) % poses.length],
      Curves.easeInOut.transform(progress),
    );
  }
}

const sceneDelaySeconds = 0.1;
const sceneTransitionSeconds = 3.0;
const sceneStepSeconds = sceneDelaySeconds + sceneTransitionSeconds;
const sceneLoopDuration = Duration(milliseconds: 12400);

/// Linkerrand van een drijvende laag na [elapsedSeconds]. De laag schuift naar
/// links en komt rechts weer binnen zodra hij helemaal links uit beeld is.
double driftedLeft({
  required double startLeft,
  required double width,
  required double screenWidth,
  required double crossingSeconds,
  required double elapsedSeconds,
}) {
  final travelled = elapsedSeconds * screenWidth / crossingSeconds;
  return (startLeft - travelled + width) % (screenWidth + width) - width;
}

/// Tekent [layers] op een canvas van [designSize], geschaald naar de beschikbare
/// ruimte en aangedreven door [animation] en, voor drijvende lagen, [drift]
/// (verstreken tijd in seconden).
class SceneStage extends StatelessWidget {
  const SceneStage({
    super.key,
    required this.designSize,
    required this.layers,
    required this.animation,
    required this.layerBuilder,
    this.drift,
  });

  final Size designSize;
  final List<SceneLayer> layers;
  final Animation<double> animation;
  final ValueListenable<double>? drift;
  final Widget Function(SceneLayer layer) layerBuilder;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final scaleX = constraints.maxWidth / designSize.width;
        final scaleY = constraints.maxHeight / designSize.height;
        final uniform = math.min(scaleX, scaleY);
        return Stack(
          fit: StackFit.expand,
          children: [
            for (final layer in layers)
              _SceneSprite(
                layer: layer,
                scaleX: scaleX,
                scaleY: scaleY,
                screenWidth: constraints.maxWidth,
                width: layer.width * (layer.stretch ? scaleX : uniform),
                height: layer.height * (layer.stretch ? scaleY : uniform),
                animation: animation,
                drift: layer.drifts ? drift : null,
                child: layerBuilder(layer),
              ),
          ],
        );
      },
    );
  }
}

class _SceneSprite extends StatelessWidget {
  const _SceneSprite({
    required this.layer,
    required this.scaleX,
    required this.scaleY,
    required this.screenWidth,
    required this.width,
    required this.height,
    required this.animation,
    required this.drift,
    required this.child,
  });

  final SceneLayer layer;
  final double scaleX;
  final double scaleY;
  final double screenWidth;
  final double width;
  final double height;
  final Animation<double> animation;
  final ValueListenable<double>? drift;
  final Widget child;

  double get _startLeft => layer.poses.first.x * scaleX - width / 2;

  Widget _posed(Pose pose) {
    final origin = layer.poses.first;
    final drift = this.drift;
    final dx = drift == null
        ? (pose.x - origin.x) * scaleX
        : driftedLeft(
                startLeft: _startLeft,
                width: width,
                screenWidth: screenWidth,
                crossingSeconds: layer.driftSeconds!,
                elapsedSeconds: drift.value,
              ) -
              _startLeft;
    return Opacity(
      opacity: layer.relativeOpacity(pose).clamp(0.0, 1.0),
      child: Transform(
        alignment: Alignment.center,
        transform: Matrix4.translationValues(
          dx,
          (pose.y - origin.y) * scaleY,
          0,
        )..rotateZ(pose.rotation * math.pi / 180),
        child: child,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final origin = layer.poses.first;
    final drift = this.drift;
    return Positioned(
      left: _startLeft,
      top: origin.y * scaleY - height / 2,
      width: width,
      height: height,
      child: layer.isAnimated || drift != null
          ? AnimatedBuilder(
              animation: Listenable.merge([animation, ?drift]),
              builder: (context, _) => _posed(layer.poseAt(animation.value)),
            )
          : _posed(origin),
    );
  }
}
