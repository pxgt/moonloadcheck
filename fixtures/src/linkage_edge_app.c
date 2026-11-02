/* SPDX-License-Identifier: Apache-2.0 */
#ifndef EXPECTED
#define EXPECTED 7
#endif
extern int api(void);
int main(int argc, char **argv) {
  (void)argv;
#ifdef LAZY_CALL
  if (argc == 1) return 0;
#else
  (void)argc;
#endif
  return api() == EXPECTED ? 0 : 41;
}
