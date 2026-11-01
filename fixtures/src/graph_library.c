#ifndef FUNCTION
#define FUNCTION api
#endif
#ifndef VALUE
#define VALUE 7
#endif
#ifdef DEPENDENCY
extern int DEPENDENCY(void);
#endif
#ifdef COUNT_LOADS
extern int loads;
__attribute__((constructor)) static void loaded(void) { ++loads; }
#endif
int FUNCTION(void) {
  int value = VALUE;
#ifdef DEPENDENCY
  value += DEPENDENCY();
#endif
  return value;
}
