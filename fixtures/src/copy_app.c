#ifndef EXPECTED
#define EXPECTED 7
#endif
extern int data[4];
extern int read_data(void);
int main(void) {
  if (data[0] != EXPECTED || data[3] != 0) return 41;
  if (read_data() != EXPECTED) return 42;
  return 0;
}
