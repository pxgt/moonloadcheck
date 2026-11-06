/* SPDX-License-Identifier: Apache-2.0 */
/* A C ABI probe of real C++ runtime exports, without depending on host headers. */
#include <stdio.h>
extern void *cpp_new(unsigned long) __asm__("_Znwm");
extern void cpp_delete(void *) __asm__("_ZdlPv");
#ifdef MODERN
extern void cpp_ios_init(void) __asm__("_ZSt21ios_base_library_initv");
#endif
int main(void) {
#ifdef MODERN
  cpp_ios_init();
#endif
  unsigned char *value = cpp_new(1);
  *value = 7;
  int ok = *value == 7;
  cpp_delete(value);
  puts("MoonLoadCheck GLIBCXX probe");
  return ok ? 0 : 1;
}
