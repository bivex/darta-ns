/// Darta feature tour — one file that exercises the main control-flow
/// constructs and representative structural edges the extractors handle. Run:
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

Future<String> relayGreeting(Future<String> source) async {
  return await source;
}

Future<String> decorateGreeting(Future<String> source) async {
  var combined = 'greeting:';
  final wrapped = _tag(await source);
  _recordTag(_tag(await source));
  combined += await source;
  if (combined.isEmpty) {
    return wrapped;
  }
  return _tag(await source);
}

int scopedCounter(int start) {
  var total = start;
  {
    final delta = 1;
    total += delta;
  }
  return total;
}

// ── 10. Local function declarations ───────────────────────────────────────────

String formatTaggedValue(int value) {
  String helper(String prefix) {
    String normalize(String raw) {
      if (raw.isEmpty) {
        return 'missing';
      }
      return raw.toUpperCase();
    }

    if (value < 0) {
      return 'NEG:${normalize(prefix)}:${-value}';
    }
    return '${normalize(prefix)}:$value';
  }

  if (value == 0) {
    return helper('zero');
  }
  return helper('value');
}

// ── 11. Class: block-body constructors, getter, setter, operator ─────────────

class Vector2 {
  static const dimensions = 2;

  final double x;
  final double y;

  // Default constructor with a block body so it appears in structural reports.
  Vector2(this.x, this.y) {
    if (!x.isFinite || !y.isFinite) {
      throw ArgumentError('coordinates must be finite');
    }
  }

  // Named constructor
  Vector2.zero() : x = 0, y = 0;

  // Named constructor with logic in both the initializer list and the body.
  Vector2.fromAngle(double radians, double length)
      : x = length * _cos(radians),
        y = length * _sin(radians) {
    if (length < 0) {
      throw ArgumentError('length must be non-negative');
    }
  }

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

// ── 12. Abstract class / getter override ─────────────────────────────────────

abstract class Shape {
  factory Shape.circle(double radius) = Circle;

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
  Rectangle.square(double side) : this(side, side);

  @override
  String get name => 'rectangle';

  @override
  double get area => width * height;
}

// ── 13. Mixin ────────────────────────────────────────────────────────────────

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

  LoggedVector.origin(String label) : super(0, 0) {
    if (label.isEmpty) {
      throw ArgumentError('label must not be empty');
    }
    log(label);
  }

  Vector2 addLogged(Vector2 other) {
    final result = this + other;
    log('added $other → $result');
    return result;
  }
}

// ── 14. Extension ────────────────────────────────────────────────────────────

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

// ── 15. yield / yield* ───────────────────────────────────────────────────────

Iterable<int> range(int start, int end) sync* {
  for (var i = start; i < end; i++) {
    yield i;
  }
}

Iterable<int> concatenate(List<Iterable<int>> sources) sync* {
  for (final src in sources) {
    yield* src;
  }
}

Stream<String> ticker(int count) async* {
  for (var i = 0; i < count; i++) {
    await Future.delayed(Duration.zero);
    yield 'tick $i';
  }
}

// ── 16. rethrow ───────────────────────────────────────────────────────────────

String parsePositive(String s) {
  try {
    final n = int.parse(s);
    if (n <= 0) {
      throw RangeError('must be positive, got $n');
    }
    return '$n';
  } on FormatException {
    rethrow;
  } catch (e) {
    return 'error: $e';
  }
}

// ── 17. assert ────────────────────────────────────────────────────────────────

double divide(double a, double b) {
  assert(b != 0, 'divisor must not be zero');
  return a / b;
}

List<int> takeN(List<int> list, int n) {
  assert(n >= 0);
  assert(n <= list.length, 'n=$n exceeds list length ${list.length}');
  return list.sublist(0, n);
}

// ── 18. break label / continue label ─────────────────────────────────────────

List<List<int>> findPairs(List<int> haystack, int target) {
  final result = <List<int>>[];
  outer:
  for (var i = 0; i < haystack.length; i++) {
    for (var j = i + 1; j < haystack.length; j++) {
      if (haystack[i] + haystack[j] == target) {
        result.add([haystack[i], haystack[j]]);
        continue outer;
      }
      if (result.length >= 10) {
        break outer;
      }
    }
  }
  return result;
}

// ── 19. throw / return styled steps ───────────────────────────────────────────

String validateAge(int age) {
  if (age < 0) {
    throw ArgumentError('age cannot be negative: $age');
  }
  if (age > 150) {
    throw ArgumentError('age seems unrealistic: $age');
  }
  return 'valid';
}

// ── 20. await for loop ─────────────────────────────────────────────────────────

Future<int> countStreamEvents() async {
  var count = 0;
  await for (final event in Stream.fromIterable([1, 2, 3])) {
    count += event;
  }
  return count;
}

// ── 21. if-case pattern matching (Dart 3) ─────────────────────────────────────

String describeJson(Object json) {
  if (json case Map<String, Object>() when json.containsKey('name')) {
    return 'JSON object with name';
  }
  if (json case List<Object>()) {
    return 'JSON array';
  }
  return 'unknown JSON type';
}

// ── 22. Pattern variable declarations (Dart 3) ────────────────────────────────

(String, int) parsePair(Object obj) {
  if (obj case (String s, int n)) {
    return (s, n);
  }
  return ('unknown', 0);
}

(int x, int y) getCoordinates(Object data) {
  var (x, y) = data;
  return (x, y);
}

// ── 23. Switch expression (Dart 3) ────────────────────────────────────────────

String classifyNumber(int n) {
  return switch (n) {
    < 0 => 'negative',
    0 => 'zero',
    > 0 => 'positive',
  };
}

String getStatus(int code) {
  return switch (code) {
    200 || 201 => 'success',
    300 || 301 => 'redirect',
    400 || 404 => 'client error',
    500 => 'server error',
    _ => 'unknown',
  };
}

// ── 24. Variables, constants, and type aliases ────────────────────────────────

typedef IntReducer = int Function(int current, int next);

const maxPreviewItems = 5;
final defaultSampleSize = 3;
var featureTourEnabled = true;

// ── 25. Enum members ───────────────────────────────────────────────────────────

enum BuildMode {
  debug,
  release;

  bool get isOptimized => this == BuildMode.release;
}

// ── 26. Extension type ────────────────────────────────────────────────────────

extension type UserLabel(String value) {
  bool get isBlank => value.isEmpty;
}

// Stubs so the file compiles independently.
final _tagLog = <String>[];

String _tag(String value) => '[$value]';

void _recordTag(String value) {
  _tagLog.add(value);
}

double _cos(double r) => r;
double _sin(double r) => r;
double _sqrt(double v) => v;
