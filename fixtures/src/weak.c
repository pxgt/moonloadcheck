/* SPDX-License-Identifier: Apache-2.0 */
extern int optional(void) __attribute__((weak));
int main(void) { return optional ? optional() : 0; }
