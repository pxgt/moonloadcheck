#ifndef VALUE
#define VALUE 7
#endif
#if defined(WEAK)
__attribute__((weak))
#elif defined(HIDDEN)
__attribute__((visibility("hidden")))
#endif
int api(void) { return VALUE; }
