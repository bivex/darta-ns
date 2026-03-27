// Dart control flow fixture

int score(int total, String category) {
  var result = 0;

  if (total > 100) {
    result = 10;
  } else if (total > 50) {
    result = 5;
  } else {
    result = 1;
  }

  while (total > 100) {
    total -= 10;
  }

  switch (category) {
    case 'A':
      result += 3;
      break;
    case 'B':
      result += 1;
      break;
    default:
      result += 0;
  }

  return result;
}

class MathBox {
  static int normalize(int input) {
    for (var i = 0; i < input; i++) {
      if (i > 50) {
        return i;
      }
    }
    return input;
  }
}
