int old_api(void) { return 7; }
int new_api(void) { return 9; }
__asm__(".symver old_api,api@SELECT_1");
__asm__(".symver new_api,api@@SELECT_2");
