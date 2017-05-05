#include "zlib.h"
#include "streams/stream_br_crafted.h"
#include <stdio.h>
#include <string.h>
#include <time.h>
#include <stdlib.h>
#include <string.h>

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
        // deflateEnd(strm);
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
        ret = deflateInit2(&(gz->strm), -1, 8, 15 + 16, 8, 0);
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
    //    gz->write ? deflateEnd(&(gz->strm)) : inflateEnd(&(gz->strm));
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

extern char * const in_files[];
extern int const arg[];
extern int const arg_len[];

int main(int argc, char *argv[]) 
{
	if (argc != 2) {
		printf("Need a number of iterations to run\n");
		return 1;
	}
	int iters = atoi(argv[1]);
	// Compression data structures that we only want to allocate once
	//
	FILE *in;
	gzFilet out = gz_opent("w");

	for (int iter = 0; iter < iters; iter++) {
    	const int *arg_ptr = arg;
    	int test_num = 0;
    	for (test_num = 0; test_num < NUM_TEST_CASES; test_num++) {
    		//fprintf(stderr, "file %s\n", in_files[test_num]);
    		in = fopen(in_files[test_num], "rb");
    		deflateReset(&(out->strm));
    		gz_compress(in, out, arg_ptr, arg_len[test_num]);
    		arg_ptr += arg_len[test_num];
    		if (*(arg_ptr - 1) != 0 || *(arg_ptr - 2) != 0) {
    			printf("prev thing doesn't end with 0,0\n");
    			exit(1);
    		}
			fclose(in);
    	}
	}

	return 0;
}
