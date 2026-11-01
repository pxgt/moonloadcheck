#ifndef EXPECTED
#define EXPECTED 7
#endif
extern int api(void);
#ifdef SECOND
extern int second(void);
#endif
int loads;
int main(void) {
  int value = api();
#ifdef SECOND
  value += second();
#endif
  if (value != EXPECTED) return 41;
#ifdef EXPECTED_LOADS
  if (loads != EXPECTED_LOADS) return 42;
#endif
  return 0;
}
