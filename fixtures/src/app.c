/* SPDX-License-Identifier: Apache-2.0 */
#ifndef ENTRY
#define ENTRY api
#define EXPECTED 7
#endif
extern int ENTRY(void);
int main(void) { return ENTRY() == EXPECTED ? 0 : 1; }
