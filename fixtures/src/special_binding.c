/* SPDX-License-Identifier: Apache-2.0 */
#ifndef NAME
#define NAME slot
#endif
#ifndef VALUE
#define VALUE 7
#endif
#ifdef TLS
#define STORAGE __thread
#else
#define STORAGE
#endif
#ifdef PROTECTED
#define VISIBILITY __attribute__((visibility("protected")))
#else
#define VISIBILITY
#endif
#ifdef CLIENT
extern STORAGE int NAME;
int api(void) { return NAME; }
#else
VISIBILITY STORAGE int NAME = VALUE;
#ifdef SELF
int api(void) { return NAME; }
#endif
#endif
