extern int call_api(void);
int api(void) { return 7; }
int main(void) { return call_api() == 7 ? 0 : 1; }
