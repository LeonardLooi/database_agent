---
name: flutter-animations
description: "Enterprise Flutter animation skill — Rive + Lottie dual-engine strategy for production mobile apps. Use when adding animations to Flutter, asking about Rive, Lottie, animated UI components, motion design, interactive states, loading indicators, onboarding flows, micro-interactions, character animations, splash screens, empty states, or any animated widget. Load BEFORE writing any Flutter animation code — enforces correct engine choice, architecture patterns, performance constraints, and accessibility."
risk: low
source: community (adapted for workspace)
date_added: "2026-03-15"
allowed-tools: Bash, Read, Write, Edit
metadata:
  triggers: animation, Rive, Lottie, animated widget, motion design, loading indicator, onboarding animation, micro-interaction, character animation, splash screen, empty state animation, interactive toggle, progress ring, skeleton loader, confetti, state machine animation
  related-skills: flutter-mobile, mobile-design, riverpod-patterns, ui-standards-tokens, accessibility-audit
  domain: frontend
  role: specialist
  scope: implementation
  output-format: code
last-reviewed: "2026-03-15"
---

## Iron Law

**RESOLVE ENGINE CHOICE FIRST (Rive vs Lottie) before writing a single line of animation code — use the decision table below. Then read the relevant reference file. Never hardcode asset paths.**

# Flutter Animations — Rive + Lottie Dual-Engine

## Engine Decision (Always resolve first)

| Use Case | Engine | Why |
|---|---|---|
| Interactive buttons, toggles, tab bars | **Rive** | State machines, pointer input |
| Onboarding with user-driven progression | **Rive** | Inputs map to gestures |
| Progress indicators tied to real data | **Rive** | Data binding at runtime |
| Auth flows (loading → success → error) | **Rive** | Multi-state without code branching |
| Games, character animations | **Rive** | 60fps, blending, bone rigs |
| Splash / intro screens (play-once) | **Lottie** | AF export, decorative |
| Empty states, "no results" illustrations | **Lottie** | Designer-owned, static loop |
| Celebration / confetti effects | **Lottie** | After Effects shine |
| Icon animations (email sent, checkmark) | **Lottie** | Simple, small JSON |
| Skeleton loaders with fixed timing | **Lottie** | Predictable, no interaction |

**If unsure:** "Does this animation need to respond to app state or user input?" Yes → Rive. No → Lottie.

---

## Package Versions

```yaml
dependencies:
  rive: ^0.14.4          # rive.app verified publisher
  lottie: ^3.3.2         # xaha.dev verified publisher
```

---

## Architecture

Never put animation controller logic directly in a screen widget. Use service + widget separation.

```
lib/
+-- core/
|   +-- animations/
|       +-- animation_assets.dart          # Typed asset path constants
|       +-- animation_preloader.dart       # Startup preloader (Rive + Lottie)
|       +-- animation_service.dart         # Unified facade for DI
|       +-- rive_controller_factory.dart   # State machine controller factory
|       +-- lottie_cache_manager.dart      # Composition cache singleton
+-- widgets/
|   +-- animations/
|       +-- rive_widget.dart               # Reusable Rive wrapper
|       +-- lottie_widget.dart             # Reusable Lottie wrappers (loop/once)
|       +-- animation_placeholder.dart     # Shimmer shown while loading
|       +-- safe_animation.dart            # Error-boundary animation widget
+-- assets/
    +-- rive/      # .riv files (< 500 KB each)
    +-- lottie/    # .json / .lottie files (< 300 KB each)
```

---

## Quick Rules (always apply)

1. **Preload on app start** — never lazy-load `.riv` or `.json` at first render
2. **Call `await RiveNative.init()` in `main()`** before `runApp`
3. **Dispose every controller** — `FileLoader`, `RiveWidgetController`, `AnimationController` must all be disposed
4. **Use `renderCache: RenderCache.raster`** for all Lottie loops
5. **Choose renderer explicitly** — `Factory.rive` for complex vector; `Factory.flutter` for simple UI
6. **Never hardcode asset paths** — use typed `AnimationAssets` constants class
7. **Wrap in error boundary** — `RiveWidgetBuilder` loading/failed states for Rive; try/catch for Lottie
8. **Semantic labels on all animations** — `Semantics(label: '...', child: ...)`
9. **Reduce motion** — check `MediaQuery.of(context).disableAnimations` and skip/pause
10. **Test with `flutter_test`** — pump and verify state transitions; mock asset loading
11. **Size budget** — `.riv` < 500 KB; `.json` < 300 KB; prefer `.lottie` (dotLottie zip) over raw JSON
12. **Multiple Rive widgets on screen** — wrap in `RivePanel(useSharedTexture: true)` for GPU performance

---

## Minimal Working Examples

### Rive — Interactive Toggle (modern API, rive ^0.14.4)

> NOTE: `RiveAnimation.asset` + `StateMachineController.fromArtboard` is the LEGACY API.
> Use `FileLoader` + `RiveWidgetController` + `RiveWidgetBuilder` for all new code.

```dart
import 'package:flutter/material.dart';
import 'package:rive/rive.dart';

class AnimatedToggle extends StatefulWidget {
  final ValueChanged<bool> onChanged;
  const AnimatedToggle({super.key, required this.onChanged});

  @override
  State<AnimatedToggle> createState() => _AnimatedToggleState();
}

class _AnimatedToggleState extends State<AnimatedToggle> {
  late final FileLoader _fileLoader;
  late final RiveWidgetController _controller;
  SMIBool? _isOnInput;
  bool _isOn = false;

  @override
  void initState() {
    super.initState();
    _fileLoader = FileLoader.fromAsset(
      AnimationAssets.toggle,
      riveFactory: Factory.rive,
    );
    _controller = RiveWidgetController(
      _fileLoader,
      artboardSelector: ArtboardSelector.byName('ToggleArtboard'),
      stateMachineSelector: StateMachineSelector.byName('Toggle'),
    );
    _isOnInput =
        _controller.stateMachine('Toggle').input<bool>('isOn') as SMIBool?;
  }

  @override
  void dispose() {
    _fileLoader.dispose();
    _controller.dispose();
    super.dispose();
  }

  void _toggle() {
    final newValue = !_isOn;
    setState(() => _isOn = newValue);
    _isOnInput?.change(newValue);
    widget.onChanged(newValue);
  }

  @override
  Widget build(BuildContext context) {
    final reduceMotion = MediaQuery.of(context).disableAnimations;
    return Semantics(
      label: 'Toggle button',
      button: true,
      child: GestureDetector(
        onTap: reduceMotion ? null : _toggle,
        child: reduceMotion
            ? _StaticToggleFallback(isOn: _isOn)
            : SizedBox(
                width: 64,
                height: 32,
                child: RiveWidgetBuilder(
                  fileLoader: _fileLoader,
                  builder: (context, state) => switch (state) {
                    RiveLoading() => const Center(
                        child: CircularProgressIndicator(strokeWidth: 2),
                      ),
                    RiveFailed() => const Icon(
                        Icons.error_outline,
                        color: Colors.red,
                        size: 20,
                      ),
                    RiveLoaded() => RiveWidget(
                        controller: _controller,
                        fit: BoxFit.contain,
                      ),
                  },
                ),
              ),
      ),
    );
  }
}
```

### Lottie — Cached Empty State

```dart
import 'package:flutter/material.dart';
import 'package:lottie/lottie.dart';

class EmptyStateAnimation extends StatefulWidget {
  final String message;
  const EmptyStateAnimation({super.key, required this.message});

  @override
  State<EmptyStateAnimation> createState() => _EmptyStateAnimationState();
}

class _EmptyStateAnimationState extends State<EmptyStateAnimation>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(vsync: this);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final reduceMotion = MediaQuery.of(context).disableAnimations;
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Semantics(
          label: 'Empty state illustration',
          child: Lottie.asset(
            AnimationAssets.emptyState,
            controller: reduceMotion ? (_controller..stop()) : _controller,
            renderCache: RenderCache.raster,
            frameRate: FrameRate.composition,
            width: 240,
            height: 240,
            fit: BoxFit.contain,
            onLoaded: (composition) {
              if (!reduceMotion) {
                _controller
                  ..duration = composition.duration
                  ..repeat();
              }
            },
          ),
        ),
        const SizedBox(height: 16),
        Text(widget.message, style: Theme.of(context).textTheme.bodyLarge),
      ],
    );
  }
}
```

### Typed Asset Constants

```dart
// lib/core/animations/animation_assets.dart
abstract final class AnimationAssets {
  // Rive
  static const String toggle       = 'assets/rive/toggle.riv';
  static const String authFlow     = 'assets/rive/auth_flow.riv';
  static const String progressRing = 'assets/rive/progress_ring.riv';
  static const String onboarding   = 'assets/rive/onboarding.riv';
  static const String bottomNav    = 'assets/rive/bottom_nav.riv';

  // Lottie
  static const String splashLogo   = 'assets/lottie/splash_logo.lottie';
  static const String emptyState   = 'assets/lottie/empty_state.lottie';
  static const String successCheck = 'assets/lottie/success_check.lottie';
  static const String errorShake   = 'assets/lottie/error_shake.lottie';
  static const String skeleton     = 'assets/lottie/skeleton.lottie';
  static const String confetti     = 'assets/lottie/confetti.lottie';
}
```

### pubspec.yaml Asset Registration

```yaml
flutter:
  assets:
    - assets/rive/
    - assets/lottie/
```

---

## When to Read Reference Files

- Building a Rive state machine, data binding, or multi-artboard flow → read `references/rive.md`
- Building a Lottie scene with dynamic color, runtime text, or performance tuning → read `references/lottie.md`
- Setting up service layer, DI, preloading, CI/CD size checks, or code review checklist → read `references/architecture.md`

---

## Related Skills

- `flutter-mobile` — Flutter 3.41.x screen patterns, Riverpod, Freezed. Load alongside for full feature context.
- `mobile-design` — Load BEFORE this skill for touch psychology and MFRI scoring
- `riverpod-patterns` — Wire animation state to Riverpod providers
- `ui-standards-tokens` — ThemeData tokens for static fallback widgets
- `accessibility-audit` — WCAG 2.1 AA audit including reduce-motion compliance
