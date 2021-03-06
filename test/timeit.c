#include "zlib.h"
#include <stdio.h>
#include <string.h>
#include <time.h>
#include <stdlib.h>

#define ROUNDS 10
#define TRIALS 100
#define WARMUPS 20
#define BUFLEN 16384
#define MAX_NAME_LEN 1024
#define MAX_UNSAFE_LEN 1024

#define local

void *myalloc(q, n, m)
    void *q;
    unsigned n, m;
{
    q = Z_NULL;
    return calloc(n, m);
}

void myfree(q, p)
    void *q, *p;
{
    q = Z_NULL;
    free(p);
}


typedef struct gzFile_st {
	// We aren't writing out to a file
    // FILE *file;
    int write;
    int err;
    char *msg;
    z_stream strm;
} *gzFilet;

const char *gzerrort(gz, err)
    gzFilet gz;
    int *err;
{
    *err = gz->err;
    return gz->msg;
}

int gzcloset(gz)
    gzFilet gz;
{
    z_stream *strm;
    unsigned char out[BUFLEN];

    if (gz == NULL)
        return Z_STREAM_ERROR;
    strm = &(gz->strm);
    if (gz->write) {
        strm->next_in = Z_NULL;
        strm->avail_in = 0;
        do {
            strm->next_out = out;
            strm->avail_out = BUFLEN;
            (void)debreach(strm, Z_FINISH);
        } while (strm->avail_out == 0);
		// Don't want to free the state
        // debreachEnd(strm);
    }
    //fclose(gz->file);
    //free(gz);
    return Z_OK;
}

gzFilet gz_opent(mode)
    const char *mode;
{
    gzFilet gz;
    int ret;

    gz = malloc(sizeof(struct gzFile_st));
    if (gz == NULL)
        return NULL;
    gz->write = strchr(mode, 'w') != NULL;
    gz->strm.zalloc = myalloc;
    gz->strm.zfree = myfree;
    gz->strm.opaque = Z_NULL;
    if (gz->write)
        ret = debreachInit2(&(gz->strm), -1, 8, 15 + 16, 8, 0);
    else {
        gz->strm.next_in = 0;
        gz->strm.avail_in = Z_NULL;
        ret = inflateInit2(&(gz->strm), 15 + 16);
    }
    if (ret != Z_OK) {
        free(gz);
        return NULL;
    }
	// Not writing out to file
    // gz->file = path == NULL ? fdopen(fd, gz->write ? "wb" : "rb") :
    //                          fopen(path, gz->write ? "wb" : "rb");
    //if (gz->file == NULL) {
    //    gz->write ? debreachEnd(&(gz->strm)) : inflateEnd(&(gz->strm));
    //    free(gz);
    //    return NULL;
    //}
    gz->err = 0;
    gz->msg = "";
    return gz;
}

void gz_compress(in, out, brs, taint_len)
    FILE   *in;
    gzFilet out;
	int *brs;
	unsigned int taint_len;
{
    local char buf[BUFLEN];
    int len;
    int err;


	if (brs != NULL)
		taint_brs(&(out->strm), brs, taint_len);

    for (;;) {
        len = (int)fread(buf, 1, sizeof(buf), in);
        if (ferror(in)) {
            perror("fread");
            exit(1);
        }
        if (len == 0) break;

        if (gzwritet(out, buf, (unsigned)len, NULL) != len) error(gzerrort(out, &err));
    }
    //fclose(in);
    if (gzcloset(out) != Z_OK) error("failed gzclose");
}

int gzwritet(gz, buf, len)
    gzFilet gz;
    const void *buf;
    unsigned len;
{
    z_stream *strm;
    unsigned char out[BUFLEN];
    if (gz == NULL || !gz->write)
        return 0;
    strm = &(gz->strm);
    strm->next_in = (void *)buf;
    strm->avail_in = len;
    do {
        strm->next_out = out;
        strm->avail_out = BUFLEN;
		(void)debreach(strm, Z_NO_FLUSH);
    } while (strm->avail_out == 0);
    return len;
}

int isNumber(str)
    char *str;
{
    char *temp = str;
    while (*temp != '\0') {
      if (isdigit((int)*temp) == 0)
	return 0;
      temp++;
    }
    return 1;
}

int charCount(str, c)
   char *str;
   char c;
{
   int ct = 0;
   char *temp = str;
   while (*temp != '\0') {
	   if (*temp == c)
		   ct++;
	   temp++;
   }
   return ct;
}

int main(argc, argv) 
	int argc;
	char *argv[];
{
	int *taint;

	int n, file_i = 2;
	if (argc == 3) {

		n = charCount(argv[1], ',') + 1;
		if (n % 2 != 0) {
			printf("Invalid argument for -b: odd number of byte values supplied.\n");
			printf("Argument: %s\n", argv[1]);
			exit(1);
		}
		// + 2 for the double null terminator
		taint = (int *) malloc(sizeof(int)*(n + 2));
		char *temp;
		int i = 0;
		while (1) {
			temp = strstr(argv[1], ",");
			if (temp == NULL) {
				if (isNumber(argv[1])) {
					taint[i] = atoi(argv[1]);
					break;
				} else {
					printf("Invalid argument for -b: %s\n", argv[1]);
					exit(1);
				}
			}
			*temp = '\0';
			if (isNumber(argv[1])) {
				taint[i] = atoi(argv[1]);
				i++;
				argv[1] = temp + 1;
			} else {
				printf("Invalid argument for -b: %s\n", argv[1]);
				exit(1);
			}
		}
		taint[n] = 0;
		taint[n + 1] = 0;
	} else {
		file_i = 1;
		taint = NULL;
	}

	// Compression data structures that we only want to allocate once
	FILE *in;
	in = fopen(argv[file_i], "rb");
	gzFilet out = gz_opent("w");

	int i, t;
	clock_t start, diff;

	for (t = 0; t < TRIALS; t++) {
    	start = clock(), diff;
    	for (i = 0; i < ROUNDS; i++) {
    		fseek(in, 0, SEEK_SET);
    		debreachReset(&(out->strm));
    		gz_compress(in, out, taint, n + 2);		
    	}
    	diff = clock() - start;
	}

	for (t = 0; t < TRIALS; t++) {
    	start = clock(), diff;
    	for (i = 0; i < ROUNDS; i++) {
    		fseek(in, 0, SEEK_SET);
    		debreachReset(&(out->strm));
    		gz_compress(in, out, taint, n + 2);		
    	}
    	diff = clock() - start;
    	printf("%d,", diff/ROUNDS);
	}

	// Cleanup
	debreachEnd(&(out->strm));
	free(out);
	fclose(in);
	free(taint);
	return 0;
}
