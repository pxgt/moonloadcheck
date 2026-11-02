/* SPDX-License-Identifier: Apache-2.0 */
#ifndef VALUE
#define VALUE 7
#endif
static int implementation(void) { return VALUE; }
static int (*resolve_api(void))(void) { return implementation; }
int api(void) __attribute__((ifunc("resolve_api")));
