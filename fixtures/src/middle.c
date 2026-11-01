/* SPDX-License-Identifier: Apache-2.0 */
extern int leaf(void);
int api(void) { return leaf(); }
int stable(void) { return 9; }
