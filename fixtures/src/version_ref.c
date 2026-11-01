extern int old_api(void);
__asm__(".symver old_api,api@SELECT_1");
int main(void) { return old_api() == 7 ? 0 : 1; }
