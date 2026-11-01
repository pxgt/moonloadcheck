#ifndef COUNT
#define COUNT 4
#endif
#ifndef VALUE
#define VALUE 7
#endif
#ifdef WEAK
#define BINDING __attribute__((weak))
#else
#define BINDING
#endif
#ifndef OMIT_DATA
BINDING int data[COUNT] = {VALUE};
int read_data(void) { return data[0]; }
#else
int read_data(void) { return 0; }
#endif
