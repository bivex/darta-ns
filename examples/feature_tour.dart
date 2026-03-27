/// Darta feature tour — one file that exercises every construct
/// the extractor currently handles. Run:
///
///   uv run darta nassi-file examples/feature_tour.dart
///
/// to produce examples/feature_tour.nassi.html.

// ── 1. Top-level function ────────────────────────────────────────────────────

int clamp(int value, int lo, int hi) {
  if (value < lo) {
    return lo;
  } else if (value > hi) {
    return hi;
  } else {
    return value;
  }
}

// ── 2. Top-level getter / setter ─────────────────────────────────────────────

int _globalCounter = 0;

int get globalCounter => _globalCounter;

set globalCounter(int v) {
  if (v < 0) {
    _globalCounter = 0;
  } else {
    _globalCounter = v;
  }
}

// ── 3. While loop ────────────────────────────────────────────────────────────

int collatz(int n) {
  var steps = 0;
  while (n != 1) {
    if (n % 2 == 0) {
      n = n ~/ 2;
    } else {
      n = 3 * n + 1;
    }
    steps++;
  }
  return steps;
}

// ── 4. Do-while loop ─────────────────────────────────────────────────────────

int nextPowerOfTwo(int n) {
  var p = 1;
  do {
    p *= 2;
  } while (p < n);
  return p;
}

// ── 5. For and for-in loops ──────────────────────────────────────────────────

int sumList(List<int> values) {
  var total = 0;
  for (var i = 0; i < values.length; i++) {
    total += values[i];
  }
  return total;
}

String joinWords(List<String> words) {
  var result = '';
  for (final w in words) {
    if (result.isNotEmpty) {
      result += ' ';
    }
    result += w;
  }
  return result;
}

// ── 6. Switch / case (classic) ───────────────────────────────────────────────

String dayName(int day) {
  switch (day) {
    case 1:
      return 'Monday';
    case 2:
      return 'Tuesday';
    case 3:
      return 'Wednesday';
    case 4:
      return 'Thursday';
    case 5:
      return 'Friday';
    default:
      return 'Weekend';
  }
}

// ── 7. Switch with Dart 3 pattern guard ──────────────────────────────────────

String classify(Object value) {
  switch (value) {
    case int n when n < 0:
      return 'negative int';
    case int n when n == 0:
      return 'zero';
    case int _:
      return 'positive int';
    case String s when s.isEmpty:
      return 'empty string';
    case String _:
      return 'non-empty string';
    default:
      return 'other';
  }
}

// ── 8. Try / on / catch / finally ────────────────────────────────────────────

String safeDivide(int a, int b) {
  try {
    if (b == 0) {
      throw ArgumentError('division by zero');
    }
    return '${a ~/ b}';
  } on ArgumentError catch (e) {
    return 'argument error: ${e.message}';
  } catch (e) {
    return 'unexpected error: $e';
  } finally {
    _globalCounter++;
  }
}

// ── 9. Async / await ─────────────────────────────────────────────────────────

Future<String> fetchGreeting(String name) async {
  await Future.delayed(Duration.zero);
  final upper = name.toUpperCase();
  return 'Hello, $upper!';
}

Future<List<int>> loadAndFilter(Future<List<int>> source) async {
  final raw = await source;
  final result = <int>[];
  for (final v in raw) {
    if (v > 0) {
      result.add(v);
    }
  }
  return result;
}

// ── 10. Class: constructor, named constructor, getter, setter, operator ───────

class Vector2 {
  final double x;
  final double y;

  // Default constructor
  Vector2(this.x, this.y);

  // Named constructor
  Vector2.zero() : x = 0, y = 0;

  // Named constructor with logic
  Vector2.fromAngle(double radians, double length)
      : x = length * _cos(radians),
        y = length * _sin(radians);

  // Factory constructor
  factory Vector2.parse(String s) {
    final parts = s.split(',');
    if (parts.length != 2) {
      throw FormatException('expected "x,y", got: $s');
    }
    return Vector2(double.parse(parts[0]), double.parse(parts[1]));
  }

  // Getter
  double get length {
    final sq = x * x + y * y;
    if (sq == 0) {
      return 0;
    }
    return _sqrt(sq);
  }

  // Setter
  set scale(double factor) {
    // immutable fields — illustrative only
    if (factor <= 0) {
      throw ArgumentError('scale must be positive');
    }
  }

  // Operator overload
  Vector2 operator +(Vector2 other) {
    return Vector2(x + other.x, y + other.y);
  }

  Vector2 operator *(double scalar) {
    if (scalar == 0) {
      return Vector2.zero();
    }
    return Vector2(x * scalar, y * scalar);
  }

  // Regular method with nested control flow
  String describe(bool verbose) {
    final len = length;
    if (verbose) {
      if (len == 0) {
        return 'zero vector';
      } else {
        return 'Vector2(x=$x, y=$y, length=$len)';
      }
    } else {
      return '($x, $y)';
    }
  }
}

// ── 11. Abstract class / getter override ─────────────────────────────────────

abstract class Shape {
  String get name;
  double get area;
}

class Circle extends Shape {
  final double radius;
  Circle(this.radius);

  @override
  String get name => 'circle';

  @override
  double get area {
    if (radius <= 0) {
      return 0;
    }
    return 3.14159 * radius * radius;
  }
}

class Rectangle extends Shape {
  final double width;
  final double height;
  Rectangle(this.width, this.height);

  @override
  String get name => 'rectangle';

  @override
  double get area => width * height;
}

// ── 12. Mixin ────────────────────────────────────────────────────────────────

mixin Loggable {
  final _log = <String>[];

  void log(String message) {
    if (message.isEmpty) {
      return;
    }
    _log.add(message);
  }

  List<String> get logs => List.unmodifiable(_log);
}

class LoggedVector extends Vector2 with Loggable {
  LoggedVector(super.x, super.y);

  Vector2 addLogged(Vector2 other) {
    final result = this + other;
    log('added $other → $result');
    return result;
  }
}

// ── 13. Extension ────────────────────────────────────────────────────────────

extension IntRangeExtension on int {
  bool isBetween(int lo, int hi) {
    if (this < lo) {
      return false;
    }
    if (this > hi) {
      return false;
    }
    return true;
  }

  List<int> to(int end) {
    final result = <int>[];
    for (var i = this; i <= end; i++) {
      result.add(i);
    }
    return result;
  }
}

// Stubs so the file compiles independently.
double _cos(double r) => r;
double _sin(double r) => r;
double _sqrt(double v) => v;
