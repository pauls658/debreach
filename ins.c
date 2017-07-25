#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <zconf.h>

#define UPDATE_HASH(s,h,c) (h = (((h)<<s->hash_shift) ^ (c)) & s->hash_mask)

struct dummy_deflate {
	unsigned int hash_shift;
	unsigned int hash_mask;	
};

int main(int argc, char *argv[]) {
	struct dummy_deflate *s, temp;
	temp.hash_shift = 6;
	temp.hash_mask = 65535;
	s = &temp;

	unsigned int ins_h;
	if (argc != 2) {
		printf("usage: %s <3-char-str>\n", argv[0]);
		exit(1);
	}

	if (strlen(argv[1]) != 3) {
		printf("input string is not three characters\n");
		exit(1);
	}

	Byte *window = argv[1];
	ins_h = window[0];
	UPDATE_HASH(s, ins_h, window[1]);
	UPDATE_HASH(s, ins_h, window[2]);
	printf("ins_h: %u\n", ins_h);

	return 0;
}
